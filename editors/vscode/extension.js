// The RustSharp extension. It starts `rustsharp --lsp` and talks to it over the Language Server Protocol.
// The client is written by hand so that the extension needs no npm packages.
'use strict';

const vscode = require('vscode');
const cp = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const LANGUAGE = 'rustsharp';
let client = null;
let output = null;
let status = null;
let diagnostics = null;

// ---- a small JSON-RPC client over stdio

class Client {
    constructor(command, args, cwd) {
        this.nextId = 1;
        this.pending = new Map();
        this.buffer = Buffer.alloc(0);
        this.onNotification = () => {};
        this.process = cp.spawn(command, args, { cwd, stdio: ['pipe', 'pipe', 'pipe'] });
        this.process.stdout.on('data', (chunk) => this.receive(chunk));
        this.process.stderr.on('data', (chunk) => output.append(chunk.toString()));
        this.process.on('error', (e) => {
            output.appendLine('rustsharp could not be started: ' + e.message);
            vscode.window.showErrorMessage(`RustSharp: could not start ${command}. Set "rustsharp.compilerPath".`);
        });
        this.process.on('exit', (code) => {
            output.appendLine(`rustsharp --lsp exited with ${code}`);
            for (const { reject } of this.pending.values()) reject(new Error('server exited'));
            this.pending.clear();
            this.exited = true;
        });
    }

    receive(chunk) {
        this.buffer = Buffer.concat([this.buffer, chunk]);
        while (true) {
            const end = this.buffer.indexOf('\r\n\r\n');
            if (end < 0) return;
            const header = this.buffer.slice(0, end).toString('ascii');
            const match = /Content-Length:\s*(\d+)/i.exec(header);
            if (!match) { this.buffer = this.buffer.slice(end + 4); continue; }
            const length = parseInt(match[1], 10);
            if (this.buffer.length < end + 4 + length) return;
            const body = this.buffer.slice(end + 4, end + 4 + length).toString('utf8');
            this.buffer = this.buffer.slice(end + 4 + length);
            let message;
            try { message = JSON.parse(body); } catch (e) { continue; }
            if (message.id !== undefined && this.pending.has(message.id)) {
                const { resolve, reject } = this.pending.get(message.id);
                this.pending.delete(message.id);
                if (message.error) reject(new Error(message.error.message));
                else resolve(message.result);
            } else if (message.method) {
                this.onNotification(message.method, message.params);
            }
        }
    }

    write(message) {
        if (this.exited) return;
        const body = Buffer.from(JSON.stringify(Object.assign({ jsonrpc: '2.0' }, message)), 'utf8');
        this.process.stdin.write(`Content-Length: ${body.length}\r\n\r\n`);
        this.process.stdin.write(body);
    }

    request(method, params) {
        const id = this.nextId++;
        return new Promise((resolve, reject) => {
            this.pending.set(id, { resolve, reject });
            this.write({ id, method, params });
        });
    }

    notify(method, params) { this.write({ method, params }); }

    async stop() {
        if (this.exited) return;
        try { await Promise.race([this.request('shutdown', null), new Promise((r) => setTimeout(r, 2000))]); } catch (e) { }
        this.notify('exit', null);
        setTimeout(() => { if (!this.exited) this.process.kill(); }, 1000);
    }
}

// ---- finding the compiler

function compiler() {
    const configured = vscode.workspace.getConfiguration('rustsharp').get('compilerPath');
    if (configured) return configured;
    for (const folder of vscode.workspace.workspaceFolders || []) {
        const candidate = path.join(folder.uri.fsPath, 'rustsharp');
        if (fs.existsSync(candidate)) return candidate;
    }
    return 'rustsharp';
}

// ---- conversions between LSP and VS Code

const toRange = (r) => new vscode.Range(r.start.line, r.start.character, r.end.line, r.end.character);
const toPosition = (p) => ({ line: p.line, character: p.character });
const textDocument = (doc) => ({ uri: doc.uri.toString() });

function toDiagnostic(d) {
    const diagnostic = new vscode.Diagnostic(toRange(d.range), d.message,
        d.severity === 2 ? vscode.DiagnosticSeverity.Warning : vscode.DiagnosticSeverity.Error);
    diagnostic.source = 'rustsharp';
    if (d.code) diagnostic.code = d.code;
    if (d.relatedInformation && d.relatedInformation.length) {
        diagnostic.relatedInformation = d.relatedInformation.map((r) =>
            new vscode.DiagnosticRelatedInformation(new vscode.Location(vscode.Uri.parse(r.location.uri), toRange(r.location.range)), r.message));
    }
    return diagnostic;
}

function toSymbol(s) {
    const symbol = new vscode.DocumentSymbol(s.name, '', Math.max(0, s.kind - 1), toRange(s.range), toRange(s.selectionRange));
    symbol.children = (s.children || []).map(toSymbol);
    return symbol;
}

// ---- the language server

function startServer(context) {
    const command = compiler();
    const cwd = (vscode.workspace.workspaceFolders || [])[0]?.uri.fsPath || os.homedir();
    output.appendLine(`starting ${command} --lsp`);
    client = new Client(command, ['--lsp'], cwd);
    client.onNotification = (method, params) => {
        if (method === 'textDocument/publishDiagnostics') {
            const list = params.diagnostics.map(toDiagnostic);
            diagnostics.set(vscode.Uri.parse(params.uri), list);
            const errors = list.filter((d) => d.severity === vscode.DiagnosticSeverity.Error).length;
            status.text = errors ? `$(error) RustSharp ${errors}` : '$(check) RustSharp';
            status.tooltip = errors ? `${errors} error(s) from the borrow checker and compiler` : 'rustsharp: no errors';
        } else if (method === 'window/logMessage') {
            output.appendLine(params.message);
        }
    };
    client.request('initialize', { processId: process.pid, rootUri: null, capabilities: {} }).then(() => {
        client.notify('initialized', {});
        for (const doc of vscode.workspace.textDocuments) open(doc);
    }, (e) => output.appendLine('initialize failed: ' + e.message));
}

function open(doc) {
    if (!client || doc.languageId !== LANGUAGE) return;
    client.notify('textDocument/didOpen', {
        textDocument: { uri: doc.uri.toString(), languageId: LANGUAGE, version: doc.version, text: doc.getText() },
    });
    status.text = '$(sync~spin) RustSharp';
}

// ---- commands

function quote(p) { return `'${p.replace(/'/g, `'\\''`)}'`; }

let terminal = null;
function run(line) {
    if (!terminal || terminal.exitStatus !== undefined) terminal = vscode.window.createTerminal('RustSharp');
    terminal.show(true);
    terminal.sendText(line);
}

async function currentFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor || editor.document.languageId !== LANGUAGE) {
        vscode.window.showWarningMessage('RustSharp: open a RustSharp file first.');
        return null;
    }
    if (editor.document.isDirty) await editor.document.save();
    return editor.document.uri.fsPath;
}

function outputPath(file, suffix) {
    const dir = path.join(os.tmpdir(), 'rustsharp');
    fs.mkdirSync(dir, { recursive: true });
    return path.join(dir, path.basename(file, path.extname(file)) + (suffix || ''));
}

function flags() {
    const config = vscode.workspace.getConfiguration('rustsharp');
    const sanitizer = config.get('sanitizer');
    if (sanitizer === 'asan') return '-O0 --asan';
    if (sanitizer === 'tsan') return '-O0 --tsan';
    return config.get('optimization') || '-O2';
}

async function showGenerated(option, extension, language) {
    const file = await currentFile();
    if (!file) return;
    const target = outputPath(file, extension);
    const args = option === '--emit-mir'
        ? [file, '--check', '--emit-mir', target]
        : [file, '-O0', '-o', outputPath(file, '.bin'), '--emit-llvm', target];
    cp.execFile(compiler(), args, { maxBuffer: 64 * 1024 * 1024 }, async (error, stdout, stderr) => {
        if (!fs.existsSync(target)) {
            vscode.window.showErrorMessage('RustSharp: the file does not compile; see the Problems panel.');
            output.append(stderr);
            return;
        }
        const doc = await vscode.workspace.openTextDocument(target);
        if (language) await vscode.languages.setTextDocumentLanguage(doc, language);
        vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: true });
    });
}

// ---- activation

function activate(context) {
    output = vscode.window.createOutputChannel('RustSharp');
    diagnostics = vscode.languages.createDiagnosticCollection('rustsharp');
    status = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
    status.text = 'RustSharp';
    status.command = 'workbench.actions.view.problems';
    status.show();
    context.subscriptions.push(output, diagnostics, status);

    startServer(context);

    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument(open),
        vscode.workspace.onDidChangeTextDocument((e) => {
            if (!client || e.document.languageId !== LANGUAGE || e.contentChanges.length === 0) return;
            client.notify('textDocument/didChange', {
                textDocument: { uri: e.document.uri.toString(), version: e.document.version },
                contentChanges: [{ text: e.document.getText() }],
            });
            status.text = '$(sync~spin) RustSharp';
        }),
        vscode.workspace.onDidCloseTextDocument((doc) => {
            if (!client || doc.languageId !== LANGUAGE) return;
            client.notify('textDocument/didClose', { textDocument: textDocument(doc) });
            diagnostics.delete(doc.uri);
        }),

        vscode.languages.registerHoverProvider(LANGUAGE, {
            async provideHover(doc, position) {
                const r = await client.request('textDocument/hover', { textDocument: textDocument(doc), position: toPosition(position) });
                if (!r) return null;
                const markdown = new vscode.MarkdownString(r.contents.value);
                return new vscode.Hover(markdown);
            },
        }),
        vscode.languages.registerDefinitionProvider(LANGUAGE, {
            async provideDefinition(doc, position) {
                const r = await client.request('textDocument/definition', { textDocument: textDocument(doc), position: toPosition(position) });
                return (r || []).map((l) => new vscode.Location(vscode.Uri.parse(l.uri), toRange(l.range)));
            },
        }),
        vscode.languages.registerCompletionItemProvider(LANGUAGE, {
            async provideCompletionItems(doc, position) {
                const r = await client.request('textDocument/completion', { textDocument: textDocument(doc), position: toPosition(position) });
                return (r || []).map((c) => {
                    const item = new vscode.CompletionItem(c.label, Math.max(0, (c.kind || 1) - 1));
                    item.detail = c.detail;
                    return item;
                });
            },
        }, '.'),
        vscode.languages.registerDocumentSymbolProvider(LANGUAGE, {
            async provideDocumentSymbols(doc) {
                const r = await client.request('textDocument/documentSymbol', { textDocument: textDocument(doc) });
                return (r || []).map(toSymbol);
            },
        }),

        vscode.commands.registerCommand('rustsharp.run', async () => {
            const file = await currentFile();
            if (!file) return;
            const exe = outputPath(file);
            run(`${quote(compiler())} ${quote(file)} ${flags()} -o ${quote(exe)} && ${quote(exe)}; echo "[exit code $?]"`);
        }),
        vscode.commands.registerCommand('rustsharp.build', async () => {
            const file = await currentFile();
            if (file) run(`${quote(compiler())} ${quote(file)} ${flags()}`);
        }),
        vscode.commands.registerCommand('rustsharp.check', async () => {
            const file = await currentFile();
            if (file) run(`${quote(compiler())} ${quote(file)} --check && echo "no errors"`);
        }),
        vscode.commands.registerCommand('rustsharp.showMir', () => showGenerated('--emit-mir', '.mir')),
        vscode.commands.registerCommand('rustsharp.showLlvm', () => showGenerated('--emit-llvm', '.ll', 'llvm')),
        vscode.commands.registerCommand('rustsharp.restartServer', async () => {
            if (client) await client.stop();
            diagnostics.clear();
            startServer(context);
        }),
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('rustsharp.compilerPath')) vscode.commands.executeCommand('rustsharp.restartServer');
        }),
    );

    context.subscriptions.push(vscode.tasks.registerTaskProvider('rustsharp', {
        provideTasks() {
            const editor = vscode.window.activeTextEditor;
            if (!editor || editor.document.languageId !== LANGUAGE) return [];
            const file = editor.document.uri.fsPath;
            const make = (name, args) => new vscode.Task({ type: 'rustsharp', file, args }, vscode.TaskScope.Workspace, name, 'rustsharp',
                new vscode.ShellExecution(compiler(), [file, ...args]), ['$rustsharp']);
            return [make('build ' + path.basename(file), flags().split(' ')), make('check ' + path.basename(file), ['--check'])];
        },
        resolveTask(task) {
            const d = task.definition;
            return new vscode.Task(d, vscode.TaskScope.Workspace, 'rustsharp ' + path.basename(d.file), 'rustsharp',
                new vscode.ShellExecution(compiler(), [d.file, ...(d.args || [])]), ['$rustsharp']);
        },
    }));
}

async function deactivate() {
    if (client) await client.stop();
}

module.exports = { activate, deactivate };

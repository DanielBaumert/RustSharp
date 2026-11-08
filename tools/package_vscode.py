#!/usr/bin/env python3
"""Packs editors/vscode into a .vsix without npm: `tools/package_vscode.py [out.vsix]`."""
import json, os, sys, zipfile
from xml.sax.saxutils import escape

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = os.path.join(root, 'editors', 'vscode')
manifest = json.load(open(os.path.join(src, 'package.json')))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'editors', f"rustsharp-{manifest['version']}.vsix")

vsixmanifest = f'''<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{manifest['name']}" Version="{manifest['version']}" Publisher="{manifest['publisher']}" />
    <DisplayName>{escape(manifest['displayName'])}</DisplayName>
    <Description xml:space="preserve">{escape(manifest['description'])}</Description>
    <Categories>{escape(','.join(manifest['categories']))}</Categories>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{manifest['engines']['vscode']}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace" />
    </Properties>
  </Metadata>
  <Installation><InstallationTarget Id="Microsoft.VisualStudio.Code" /></Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
  </Assets>
</PackageManifest>
'''
types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension=".json" ContentType="application/json" />
  <Default Extension=".js" ContentType="application/javascript" />
  <Default Extension=".md" ContentType="text/markdown" />
  <Default Extension=".vsixmanifest" ContentType="text/xml" />
</Types>
'''
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', types)
    z.writestr('extension.vsixmanifest', vsixmanifest)
    for dirpath, _, files in os.walk(src):
        for f in sorted(files):
            if f.endswith('.vsix'): continue
            full = os.path.join(dirpath, f)
            z.write(full, 'extension/' + os.path.relpath(full, src))
print(out)

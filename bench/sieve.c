#include <stdio.h>
#include <stdlib.h>
typedef struct { long hdr; int v; } Item;
static int sieve(int n){ char*f=calloc(n+1,1); int c=0; for(int i=2;i<=n;i++){ if(f[i])continue; c++; for(long j=(long)i*i;j<=n;j+=i)f[j]=1; } free(f); return c; }
static long owned(int rounds){ long s=0; for(int r=0;r<rounds;r++){ int cap=0,n=0; Item**l=0; for(int i=0;i<1000;i++){ if(n==cap){cap=cap?cap*2:4;l=realloc(l,cap*sizeof(Item*));} Item*it=calloc(1,sizeof(Item)); it->v=i; l[n++]=it; } for(int i=0;i<n;i++)s+=l[i]->v; for(int i=0;i<n;i++)free(l[i]); free(l);} return s; }
int main(){ printf("%d\n%ld\n",sieve(100000000),owned(20000)); }

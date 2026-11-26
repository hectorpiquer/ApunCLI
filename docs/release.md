# Flujo de release de apuncli

Así se preparó (y se prepara) cada versión, tal y como pide el curso: la rama,
el PR que pasa por Actions en los tres sistemas, la etiqueta y la release.

```
main ──(trabajo diario, commits pequeños)──▶ rama release-1.0
                                               │  CHANGELOG + versión en pyproject/__init__
                                               ▼
                                        PR → Actions (ubuntu · windows · macOS)
                                               │  verde en los tres
                                               ▼
                                        merge ──▶ main
                                               │
                                               ▼
                git tag -a v1.0.0 -m "apuncli 1.0.0 …"   (el tag apunta al merge)
                git push origin v1.0.0
                gh release create v1.0.0 --title "apuncli v1.0.0" \
                    --notes-file CHANGELOG-<versión>   (o pegar el bloque del CHANGELOG)
```

De la rama `release-1.0` salieron todos los cortes: v1.0.0 (PR #1),
v1.0.1 (hotfix), v1.0.2 (PR #3, auditoría), v1.0.3 y v1.0.4. La rama queda
como testigo del flujo.

## Lo que promete la v1.0 (SemVer)

- Las órdenes y el **esquema de `acciones.json`** no cambian sin subir a 2.0.0.
- Los códigos de salida 0/1/2/3/4 no cambian.
- Los parches (1.0.x) arreglan y añaden sin romper: prueba en CI en tres
  sistemas antes de mergear, siempre.

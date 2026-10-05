# Pokémon Platinum ES Casino Patcher

Restaura las tragaperras del casino de Ciudad Rocavelo en **Pokémon Platino, edición española**. Acepta una ROM `.nds` o un `.zip` con una sola ROM. Se aplica localmente, sin subir archivos a ningún servicio.

El proyecto contiene el parche BPS y el código del parcheador. Necesitas aportar tu propia ROM original.

<img width="1280" height="1112" alt="imagen" src="https://github.com/user-attachments/assets/2057d627-f57c-4c4b-8cc4-263891b12e4b" />


## Uso con ventana

### Windows: ejecutable (sin instalar Python)

**No necesitas tener Python instalado para usar `PlatinumCasinoPatcher.exe`.** El ejecutable incluye todo lo necesario.

1. Descarga `PlatinumCasinoPatcher-windows.zip` desde [Releases](https://github.com/ElGundamTrampa/pokemon-platinum-es-casino-patcher/releases/latest).
2. Descomprime el ZIP en una carpeta.
3. Abre `PlatinumCasinoPatcher.exe`.
4. Pulsa **Seleccionar ROM y restaurar casino** y elige tu `.nds` o `.zip` original.

La salida se guarda en una carpeta `casino-restaurado` junto al archivo de entrada. Conserva el nombre de la ROM interna del ZIP para facilitar el uso de partidas existentes. Si el destino ya existe, el parcheador se detiene.

### Código fuente: requiere Python

Instala Python 3.10 o posterior con Tkinter (incluido en el instalador habitual de Python para Windows). Descarga el proyecto completo y ejecuta:

```console
python casino_patcher.py
```

En Windows también puedes abrir `Iniciar parcheador.bat`. **El `.bat` y los archivos `.py` sí requieren Python instalado**, a diferencia del `.exe`. La ventana y el funcionamiento son los mismos.

Para generar un ejecutable de Windows sin instalar Python en el equipo de destino, utiliza el flujo manual **Windows executable** de GitHub Actions. Su artefacto incluye `PlatinumCasinoPatcher.exe`: descomprime la descarga y abre ese archivo para usar la ventana. También puedes aplicar el BPS con otro parcheador compatible.

## Uso por comandos

Estos ejemplos ejecutan el código fuente y requieren Python 3.10 o posterior:

```console
python casino_patcher.py "Pokemon - Platinum Version_OG.zip"
python casino_patcher.py "original.nds" --output "restaurada.nds"
python casino_patcher.py "original.zip" --output "restaurada.zip"
```

La salida puede ser `.nds` o `.zip`, independientemente del formato de entrada. El archivo original no se sobrescribe. Las partidas `.sav` y los estados rápidos no son entradas del parcheador.

## Versión compatible

Solo se admite la ROM española original verificada, sin recortar y sin otros parches:

| Dato | Valor |
| --- | --- |
| Código del juego | `CPUS` |
| Tamaño | 134 217 728 bytes (128 MiB) |
| SHA-256 original | `b420059bb0b982e7ddcc9d33f21b85547e443f77f6424ff0ff7522d386d05fab` |
| SHA-256 restaurada | `c9505e3dc0b8a57d7bb9a9744a799c8a618e7f6bc0904f98d7a513545f120d82` |

La comprobación del hash se realiza sobre el `.nds`, también cuando está dentro de un ZIP. Una ROM ya restaurada se detecta y se rechaza. Otras regiones o revisiones requieren otro parche.

## Partidas existentes

1. Respalda tu `.sav` antes de sustituir el juego.
2. Instala la ROM restaurada conservando el **mismo nombre y la misma ruta** que utilizabas antes.
3. Inicia el juego y selecciona **Continuar**. Lleva el **Monedero** para jugar.
4. Comprueba que entra al minijuego y que vuelve correctamente al casino antes de guardar de nuevo.

Si sigue apareciendo «¡Es una máquina recreativa!», comprueba que el archivo instalado corresponde al SHA-256 restaurado de la tabla anterior y que se está abriendo esa copia. Si aparece «Partida nueva», verifica que tu `.sav` conserva el nombre y la ubicación esperados. No sustituyas un guardado válido por uno vacío.

## Qué restaura y qué se ha comprobado

El parche modifica las 12 interacciones de las máquinas, los textos del casino y sus recursos gráficos. Modifica únicamente estos archivos internos de la ROM:

- `fielddata/script/scr_seq.narc`
- `msgdata/pl_msg.narc`
- `resource/spa/slot/slot.narc`

Se verificó que el resultado coincide byte por byte con la ROM restaurada probada. Se confirmó la carga de una partida existente y la entrada al minijuego. No se afirma una prueba completa de todas las rondas o premios.

## Desarrollo

El parcheador solo requiere la biblioteca estándar de Python. Las pruebas pequeñas usan datos sintéticos, sin ROMs:

```console
python -m unittest discover -s tests -v
```

El BPS se puede regenerar a partir de las dos ROMs locales verificadas:

```console
python tools/build_patch.py "original.nds" "restaurada.nds" "patches/platinum-es-casino-v1.bps"
```

El generador comprueba los SHA-256 y aplica el parche recién creado antes de escribirlo. El archivo de destino debe ser nuevo.

## Créditos y licencia

Código propio del parcheador: [MIT](LICENSE), © 2026 ElGundamTrampa.

La licencia MIT del código no otorga derechos sobre los recursos de Pokémon contenidos en el parche ni sobre las ROMs. Pokémon pertenece a sus respectivos titulares. Este es un proyecto no oficial.

El trabajo de restauración se apoyó en [pret/pokeplatinum](https://github.com/pret/pokeplatinum), especialmente los scripts del casino, la tabla de caracteres y el recurso `slot.narc`. El formato BPS se implementó a partir de la [especificación de byuu, en dominio público](https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md).

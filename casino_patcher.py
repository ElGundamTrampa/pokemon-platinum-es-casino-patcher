"""Restore the Spanish Pokémon Platinum Game Corner from a verified ROM."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import queue
import sys
import tempfile
import threading
import zipfile

from bps import PatchError, apply_bps

VERSION = "1.0.0"
ROM_SIZE = 134_217_728
SOURCE_SHA256 = "b420059bb0b982e7ddcc9d33f21b85547e443f77f6424ff0ff7522d386d05fab"
TARGET_SHA256 = "c9505e3dc0b8a57d7bb9a9744a799c8a618e7f6bc0904f98d7a513545f120d82"
PATCH_NAME = "platinum-es-casino-v1.bps"


def read_rom(path: Path) -> tuple[bytes, str]:
    """Read one ROM without extracting ZIP members onto the filesystem."""
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                entries = [e for e in archive.infolist() if not e.is_dir()
                           and e.filename.lower().endswith(".nds")]
                if len(entries) != 1:
                    raise PatchError("El ZIP debe contener exactamente una ROM .nds")
                entry = entries[0]
                if entry.file_size != ROM_SIZE:
                    raise PatchError("La ROM del ZIP debe ocupar 128 MiB")
                if entry.flag_bits & 1:
                    raise PatchError("No se admiten ZIP protegidos por contraseña")
                name = PurePosixPath(entry.filename.replace("\\", "/")).name
                with archive.open(entry) as stream:
                    data = stream.read(ROM_SIZE + 1)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
            raise PatchError(f"No se pudo leer el ZIP: {error}") from error
    elif path.suffix.lower() == ".nds":
        if path.stat().st_size != ROM_SIZE:
            raise PatchError("La ROM debe ocupar 128 MiB")
        with path.open("rb") as stream:
            data = stream.read(ROM_SIZE + 1)
        name = path.name
    else:
        raise PatchError("Selecciona un archivo .nds o .zip")
    if len(data) != ROM_SIZE:
        raise PatchError("Tamaño de ROM inesperado")
    digest = hashlib.sha256(data).hexdigest()
    if digest == TARGET_SHA256:
        raise PatchError("Esta ROM ya tiene el casino restaurado")
    if data[12:16] != b"CPUS" or digest != SOURCE_SHA256:
        raise PatchError("Esta ROM no es la edición española original compatible.\n"
                         f"SHA-256 detectado: {digest}\n"
                         "No se admiten otras regiones, ROMs recortadas ni otros hacks.")
    return data, name


def default_output(source: Path, rom_name: str) -> Path:
    suffix = ".zip" if source.suffix.lower() == ".zip" else ".nds"
    return source.parent / "casino-restaurado" / (Path(rom_name).stem + suffix)


def write_output(destination: Path, rom_name: str, data: bytes) -> None:
    """Write and validate a temporary output, then publish without overwriting."""
    if destination.suffix.lower() not in (".nds", ".zip"):
        raise PatchError("La salida debe tener extensión .nds o .zip")
    if destination.exists():
        raise PatchError("El archivo de salida ya existe. Elige otro nombre o carpeta.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".casino-", dir=destination.parent)
    temporary = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            if destination.suffix.lower() == ".zip":
                with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                    archive.writestr(rom_name, data)
            else:
                stream.write(data)
        if destination.suffix.lower() == ".zip":
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise PatchError("La comprobación del ZIP de salida ha fallado")
        # Exclusive creation protects the original and any concurrently created file.
        created = False
        try:
            with destination.open("xb") as output:
                created = True
                with temporary.open("rb") as stream:
                    while block := stream.read(1024 * 1024):
                        output.write(block)
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
    finally:
        temporary.unlink(missing_ok=True)


def patch_rom(source: Path, destination: Path | None = None, status=print) -> Path:
    status("Comprobando la ROM original…")
    original, rom_name = read_rom(source)
    destination = destination or default_output(source, rom_name)
    if source.resolve() == destination.resolve():
        raise PatchError("La salida debe ser un archivo diferente del original")
    if destination.exists():
        raise PatchError("El archivo de salida ya existe. Elige otro destino.")
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    status("Restaurando el casino…")
    restored = apply_bps(original, (root / "patches" / PATCH_NAME).read_bytes(), max_size=ROM_SIZE)
    if hashlib.sha256(restored).hexdigest() != TARGET_SHA256:
        raise PatchError("La ROM restaurada no coincide con la versión verificada")
    status("Guardando y verificando la salida…")
    write_output(destination, rom_name, restored)
    return destination


def launch_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError:
        print("Tkinter no está disponible. Usa la versión por comandos.", file=sys.stderr)
        return 1
    window = tk.Tk()
    window.title(f"Casino de Pokémon Platino ES — {VERSION}")
    window.geometry("640x370")
    window.minsize(540, 350)
    frame = ttk.Frame(window, padding=24)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Restaura el casino de Pokémon Platino", font=("Segoe UI", 16)).pack(anchor="w")
    ttk.Label(frame, text="Edición española · ROM original de 128 MiB\nSelecciona tu archivo .nds o .zip.",
              wraplength=550).pack(anchor="w", pady=(12, 18))
    info = tk.StringVar(value="La salida se guarda en una carpeta nueva llamada casino-restaurado.")
    ttk.Label(frame, textvariable=info, wraplength=550).pack(anchor="w", pady=(0, 14))
    messages: queue.Queue = queue.Queue()
    closing = False
    working = False

    def choose() -> None:
        nonlocal working
        name = filedialog.askopenfilename(title="Selecciona la ROM original",
            filetypes=[("ROM de Nintendo DS", "*.nds *.zip"), ("Todos los archivos", "*.*")])
        if not name:
            return
        working = True
        button.configure(state="disabled")
        progress.configure(mode="indeterminate", value=0)
        progress.start()

        def worker() -> None:
            try:
                path = patch_rom(Path(name), status=lambda text: messages.put(("status", text)))
                messages.put(("done", str(path)))
            except Exception as error:
                messages.put(("error", str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll() -> None:
        nonlocal working
        try:
            while True:
                kind, value = messages.get_nowait()
                if kind == "status":
                    info.set(value)
                else:
                    working = False
                    progress.stop()
                    progress.configure(mode="determinate", value=0)
                    button.configure(state="normal")
                    if kind == "done":
                        info.set(f"ROM restaurada:\n{value}")
                        messagebox.showinfo("Casino restaurado", f"Archivo generado:\n{value}\n\n"
                            "Continúa desde el guardado del juego, con Monedero.")
                    else:
                        info.set("No se ha generado la ROM restaurada.")
                        messagebox.showerror("No se pudo aplicar el parche", value)
        except queue.Empty:
            pass
        if not closing:
            window.after(100, poll)

    def close() -> None:
        nonlocal closing
        if working:
            messagebox.showinfo("Parche en curso", "Espera a que termine la operación antes de cerrar.")
            return
        closing = True
        window.destroy()

    button = ttk.Button(frame, text="Seleccionar ROM y restaurar casino", command=choose)
    button.pack(anchor="w", pady=8)
    progress = ttk.Progressbar(frame, mode="determinate", value=0)
    progress.pack(fill="x", pady=12)
    ttk.Label(frame, text="Conserva el nombre y la ruta del juego al instalarlo.\n"
              "Haz una copia de tu .sav antes de sustituir la ROM.", wraplength=550).pack(anchor="w")
    window.protocol("WM_DELETE_WINDOW", close)
    window.after(100, poll)
    window.mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restaurar el casino de Pokémon Platino español.")
    parser.add_argument("rom", nargs="?", type=Path, help="ROM original .nds o ZIP con una .nds")
    parser.add_argument("-o", "--output", type=Path, help="Archivo nuevo de salida .nds o .zip")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    if args.rom is None:
        if args.output:
            parser.error("--output requiere una ROM de entrada")
        return launch_gui()
    try:
        destination = patch_rom(args.rom, args.output)
    except (OSError, PatchError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Casino restaurado: {destination}")
    print(f"SHA-256 de la ROM: {TARGET_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

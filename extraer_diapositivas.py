import argparse
import base64
import json
import re
from pathlib import Path


def encontrar_bloque_diapositivas(contenido: str) -> str:
    patron = re.compile(r"const\s+diapositivas\s*=\s*(\[[\s\S]*?\]);", re.MULTILINE)
    coincidencia = patron.search(contenido)
    if not coincidencia:
        raise ValueError("No se encontró la constante 'diapositivas' en el HTML.")
    return coincidencia.group(1)


def parsear_diapositivas(bloque_json: str) -> list:
    try:
        return json.loads(bloque_json)
    except json.JSONDecodeError as error:
        raise ValueError(f"No se pudo parsear la constante 'diapositivas': {error}") from error


def extraer_png_data_uri(data_uri: str) -> bytes:
    patron = re.compile(r"^data:image/(?P<formato>[a-zA-Z0-9.+-]+);base64,(?P<data>[A-Za-z0-9+/=\s]+)$", re.DOTALL)
    coincidencia = patron.match(data_uri.strip())
    if not coincidencia:
        raise ValueError("La imagen no está en formato data URI válido.")

    formato = coincidencia.group("formato").lower()
    if formato != "png":
        raise ValueError(f"Formato no soportado: {formato}. Solo se admite PNG.")

    datos_base64 = re.sub(r"\s+", "", coincidencia.group("data"))
    return base64.b64decode(datos_base64, validate=True)


def buscar_html_con_diapositivas(directorio: Path) -> Path | None:
    for archivo_html in sorted(directorio.glob("*.html")):
        try:
            contenido = archivo_html.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            contenido = archivo_html.read_text(encoding="latin-1")

        if re.search(r"const\s+diapositivas\s*=", contenido):
            return archivo_html
    return None


def extraer_diapositivas(html_path: Path, output_dir_png: Path, output_dir_txt: Path) -> tuple[int, int]:
    try:
        contenido = html_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        contenido = html_path.read_text(encoding="latin-1")

    bloque = encontrar_bloque_diapositivas(contenido)
    diapositivas = parsear_diapositivas(bloque)

    output_dir_png.mkdir(parents=True, exist_ok=True)
    output_dir_txt.mkdir(parents=True, exist_ok=True)

    png_guardados = 0
    txt_guardados = 0
    for indice, diapositiva in enumerate(diapositivas, start=1):
        if not isinstance(diapositiva, dict):
            continue

        data_uri = diapositiva.get("imagen")
        if not isinstance(data_uri, str):
            continue

        try:
            datos_png = extraer_png_data_uri(data_uri)
        except Exception as error:
            print(f"[WARN] Saltando diapositiva {indice}: {error}")
            continue

        nombre_base = f"diapositiva{indice}"

        destino_png = output_dir_png / f"{nombre_base}.png"
        destino_png.write_bytes(datos_png)
        png_guardados += 1

        texto = diapositiva.get("texto", "")
        if not isinstance(texto, str):
            texto = str(texto)
        destino_txt = output_dir_txt / f"{nombre_base}.txt"
        destino_txt.write_text(texto, encoding="utf-8")
        txt_guardados += 1

    return png_guardados, txt_guardados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrae imágenes de la constante 'diapositivas' en un HTML y las guarda como PNG."
    )
    parser.add_argument(
        "--html",
        type=Path,
        help="Ruta del archivo HTML. Si no se indica, se busca automáticamente en la carpeta actual.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("diapositivas_png"),
        help="Carpeta de salida para los PNG (por defecto: diapositivas_png).",
    )
    parser.add_argument(
        "--out-textos",
        type=Path,
        default=Path("diapositivas_txt"),
        help="Carpeta de salida para los TXT (por defecto: diapositivas_txt).",
    )
    args = parser.parse_args()

    html_path = args.html
    if html_path is None:
        encontrado = buscar_html_con_diapositivas(Path.cwd())
        if not encontrado:
            raise SystemExit("No se encontró ningún .html con la constante 'diapositivas' en la carpeta actual.")
        html_path = encontrado

    if not html_path.exists():
        raise SystemExit(f"No existe el archivo HTML: {html_path}")

    cantidad_png, cantidad_txt = extraer_diapositivas(html_path, args.out, args.out_textos)
    print(f"Listo. Se guardaron {cantidad_png} PNG en: {args.out.resolve()}")
    print(f"Listo. Se guardaron {cantidad_txt} TXT en: {args.out_textos.resolve()}")


if __name__ == "__main__":
    main()
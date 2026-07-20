from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        # Permite builds repetidos cuando el parche ya fue aplicado.
        if new in text:
            print(f"{label}: ya aplicado")
            return text
        raise RuntimeError(f"No se encontró el bloque requerido: {label}")
    if count != 1:
        raise RuntimeError(f"El bloque {label} aparece {count} veces")
    print(f"{label}: aplicado")
    return text.replace(old, new, 1)


def main() -> None:
    text = APP.read_text(encoding="utf-8")

    old_connect = '''    def _connect(self) -> None:\n        self.connect_button.configure(state="disabled")\n        self._set_status("Conectando...")\n\n        def task() -> None:\n            try:\n                protocol = self.client.connect(self._connection_config())\n'''
    new_connect = '''    def _connect(self) -> None:\n        try:\n            config = self._connection_config()\n        except Exception as exc:\n            messagebox.showerror("Configuración de conexión", str(exc))\n            return\n        self.connect_button.configure(state="disabled")\n        self._set_status("Conectando...")\n\n        def task() -> None:\n            try:\n                protocol = self.client.connect(config)\n'''
    text = replace_once(text, old_connect, new_connect, "configuración segura de conexión")

    old_report = '''        output = Path(filedialog.asksaveasfilename(\n            title="Guardar informe AUTOGUARD",\n            defaultextension=".pdf",\n            filetypes=[("Documento PDF", "*.pdf")],\n            initialfile=default_report_path().name,\n            initialdir=str(default_report_path().parent),\n        ))\n        if not str(output):\n            return\n'''
    new_report = '''        raw_output = filedialog.asksaveasfilename(\n            title="Guardar informe AUTOGUARD",\n            defaultextension=".pdf",\n            filetypes=[("Documento PDF", "*.pdf")],\n            initialfile=default_report_path().name,\n            initialdir=str(default_report_path().parent),\n        )\n        if not raw_output:\n            return\n        output = Path(raw_output)\n'''
    text = replace_once(text, old_report, new_report, "cancelación segura del informe PDF")

    APP.write_text(text, encoding="utf-8", newline="\n")
    print("Fuente preparada para compilación")


if __name__ == "__main__":
    main()

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from wallet_store import (
    InvalidMasterPassword,
    WalletStore,
    WalletStoreError,
)


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "data" / "wallets.db"
BSCSCAN_ADDRESS_URL = "https://bscscan.com/address/{address}"


class BSCWalletGUI:
    def __init__(self, root: tk.Tk, store: WalletStore) -> None:
        self.root = root
        self.store = store

        self.root.title("BSC Wallet Manager")
        self.root.geometry("1060x650")
        self.root.minsize(900, 540)

        self.label_var = tk.StringVar()
        self.quantity_var = tk.StringVar(value="1")
        self.status_var = tk.StringVar(value="Listo")

        self._configure_style()
        self._build_ui()
        self.refresh_wallets()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        available = style.theme_names()
        if "vista" in available:
            style.theme_use("vista")
        elif "clam" in available:
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=30)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="BSC Wallet Manager",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Genera wallets EVM/BSC, guarda las claves cifradas localmente "
                "y abre cada dirección en BscScan."
            ),
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 14))

        create_box = ttk.LabelFrame(outer, text="Crear wallets", padding=12)
        create_box.pack(fill="x", pady=(0, 14))

        ttk.Label(create_box, text="Etiqueta").grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        label_entry = ttk.Entry(
            create_box,
            textvariable=self.label_var,
            width=34,
        )
        label_entry.grid(row=0, column=1, sticky="ew", padx=(0, 16))

        ttk.Label(create_box, text="Cantidad").grid(
            row=0, column=2, sticky="w", padx=(0, 8)
        )
        qty = ttk.Spinbox(
            create_box,
            from_=1,
            to=100,
            textvariable=self.quantity_var,
            width=7,
        )
        qty.grid(row=0, column=3, sticky="w", padx=(0, 16))

        ttk.Button(
            create_box,
            text="Crear wallet(s)",
            command=self.create_wallets,
        ).grid(row=0, column=4, sticky="e")

        create_box.columnconfigure(1, weight=1)

        table_box = ttk.Frame(outer)
        table_box.pack(fill="both", expand=True)

        columns = ("id", "label", "address", "created")
        self.tree = ttk.Treeview(
            table_box,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("id", text="ID")
        self.tree.heading("label", text="Etiqueta")
        self.tree.heading("address", text="Dirección BSC")
        self.tree.heading("created", text="Creada (UTC)")

        self.tree.column("id", width=60, anchor="center", stretch=False)
        self.tree.column("label", width=180)
        self.tree.column("address", width=430)
        self.tree.column("created", width=210)

        y_scroll = ttk.Scrollbar(
            table_box,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=y_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        y_scroll.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda _event: self.open_bscscan())

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(12, 0))

        ttk.Button(
            actions,
            text="Abrir en BscScan",
            command=self.open_bscscan,
        ).pack(side="left")

        ttk.Button(
            actions,
            text="Copiar dirección",
            command=self.copy_address,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            actions,
            text="Ver clave privada",
            command=self.show_private_key,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            actions,
            text="Actualizar lista",
            command=self.refresh_wallets,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            actions,
            textvariable=self.status_var,
        ).pack(side="right")

    def _selected_wallet_id(self) -> int | None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("BSC Wallet Manager", "Seleccioná una wallet.")
            return None
        return int(selected[0])

    def _selected_wallet(self) -> dict | None:
        wallet_id = self._selected_wallet_id()
        if wallet_id is None:
            return None
        wallet = self.store.get_wallet(wallet_id)
        if wallet is None:
            messagebox.showerror("Error", "La wallet ya no existe.")
        return wallet

    def refresh_wallets(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        wallets = self.store.list_wallets()
        for wallet in wallets:
            self.tree.insert(
                "",
                "end",
                iid=str(wallet["id"]),
                values=(
                    wallet["id"],
                    wallet["label"],
                    wallet["address"],
                    wallet["created_at"],
                ),
            )

        self.status_var.set(f"{len(wallets)} wallet(s)")

    def create_wallets(self) -> None:
        try:
            quantity = int(self.quantity_var.get())
            if quantity < 1 or quantity > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Cantidad inválida",
                "La cantidad debe ser un número entre 1 y 100.",
            )
            return

        base_label = self.label_var.get().strip()
        existing = len(self.store.list_wallets())

        try:
            for index in range(quantity):
                if base_label:
                    label = (
                        base_label
                        if quantity == 1
                        else f"{base_label} {index + 1}"
                    )
                else:
                    label = f"Wallet {existing + index + 1}"
                self.store.create_wallet(label)
        except WalletStoreError as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.label_var.set("")
        self.refresh_wallets()
        self.status_var.set(f"{quantity} wallet(s) creada(s)")

    def open_bscscan(self) -> None:
        wallet = self._selected_wallet()
        if wallet is None:
            return

        url = BSCSCAN_ADDRESS_URL.format(address=wallet["address"])
        webbrowser.open_new_tab(url)
        self.status_var.set("BscScan abierto en el navegador")

    def copy_address(self) -> None:
        wallet = self._selected_wallet()
        if wallet is None:
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(wallet["address"])
        self.root.update()
        self.status_var.set("Dirección copiada")

    def show_private_key(self) -> None:
        wallet_id = self._selected_wallet_id()
        if wallet_id is None:
            return

        if not messagebox.askyesno(
            "Advertencia",
            "La clave privada controla los fondos de esta wallet. "
            "¿Querés mostrarla?",
            icon="warning",
        ):
            return

        try:
            private_key = self.store.get_private_key(wallet_id)
        except WalletStoreError as exc:
            messagebox.showerror("Error", str(exc))
            return

        popup = tk.Toplevel(self.root)
        popup.title("Clave privada")
        popup.geometry("720x180")
        popup.resizable(False, False)
        popup.transient(self.root)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="No compartas esta clave ni la pegues en sitios web.",
        ).pack(anchor="w", pady=(0, 10))

        key_var = tk.StringVar(value=private_key)
        entry = ttk.Entry(
            frame,
            textvariable=key_var,
            state="readonly",
            width=90,
        )
        entry.pack(fill="x")

        def copy_key() -> None:
            popup.clipboard_clear()
            popup.clipboard_append(private_key)
            popup.update()
            messagebox.showinfo("Copiada", "Clave privada copiada al portapapeles.")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons,
            text="Copiar clave",
            command=copy_key,
        ).pack(side="left")

        ttk.Button(
            buttons,
            text="Cerrar",
            command=popup.destroy,
        ).pack(side="right")


def setup_or_unlock(root: tk.Tk, store: WalletStore) -> bool:
    root.withdraw()

    if not store.is_initialized():
        messagebox.showinfo(
            "Primer inicio",
            "Creá una contraseña maestra. Se usará para cifrar las claves privadas "
            "guardadas en este equipo.",
        )

        while True:
            password = simpledialog.askstring(
                "Contraseña maestra",
                "Nueva contraseña maestra (mínimo 10 caracteres):",
                show="*",
                parent=root,
            )
            if password is None:
                return False

            confirmation = simpledialog.askstring(
                "Confirmar contraseña",
                "Repetí la contraseña maestra:",
                show="*",
                parent=root,
            )
            if confirmation is None:
                return False

            if password != confirmation:
                messagebox.showerror(
                    "Error",
                    "Las contraseñas no coinciden.",
                )
                continue

            try:
                store.setup(password)
                break
            except WalletStoreError as exc:
                messagebox.showerror("Error", str(exc))
    else:
        attempts = 0
        while attempts < 5:
            password = simpledialog.askstring(
                "Desbloquear",
                "Contraseña maestra:",
                show="*",
                parent=root,
            )
            if password is None:
                return False

            try:
                store.unlock(password)
                break
            except InvalidMasterPassword:
                attempts += 1
                messagebox.showerror(
                    "Error",
                    "Contraseña maestra incorrecta.",
                )
        else:
            messagebox.showerror(
                "Bloqueado",
                "Demasiados intentos fallidos.",
            )
            return False

    root.deiconify()
    return True


def main() -> int:
    root = tk.Tk()
    store = WalletStore(DB_PATH)

    try:
        if not setup_or_unlock(root, store):
            root.destroy()
            return 1

        BSCWalletGUI(root, store)

        def shutdown() -> None:
            store.close()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", shutdown)
        root.mainloop()
        return 0
    finally:
        try:
            store.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

import tkinter as tk
from pathlib import Path

from eth_account import Account

import app
from wallet_store import WalletStore


def test_gui_creates_wallets_and_opens_bscscan(tmp_path: Path, monkeypatch) -> None:
    store = WalletStore(tmp_path / "wallets.db")
    store.setup("correct horse battery staple")

    root = tk.Tk()
    root.withdraw()

    try:
        gui = app.BSCWalletGUI(root, store)
        gui.label_var.set("Cliente")
        gui.quantity_var.set("2")
        gui.create_wallets()
        root.update_idletasks()

        wallets = store.list_wallets()
        assert len(wallets) == 2
        assert len(gui.tree.get_children()) == 2

        for wallet in wallets:
            assert wallet["address"].startswith("0x")
            assert len(wallet["address"]) == 42
            # Re-parse the generated address through eth-account to verify
            # that it is a valid EVM/BSC account.
            assert Account.from_key(store.get_private_key(wallet["id"])).address == wallet["address"]

        first_item = gui.tree.get_children()[0]
        gui.tree.selection_set(first_item)

        opened = []
        monkeypatch.setattr(app.webbrowser, "open_new_tab", opened.append)
        gui.open_bscscan()

        selected = store.get_wallet(int(first_item))
        assert selected is not None
        assert opened == [
            f"https://bscscan.com/address/{selected['address']}"
        ]
        assert gui.status_var.get() == "BscScan abierto en el navegador"
    finally:
        root.destroy()
        store.close()

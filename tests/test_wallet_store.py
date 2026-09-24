from pathlib import Path

import pytest
from eth_account import Account

from wallet_store import InvalidMasterPassword, WalletStore


def test_create_persist_and_decrypt_wallet(tmp_path: Path) -> None:
    db_path = tmp_path / "wallets.db"

    store = WalletStore(db_path)
    store.setup("correct horse battery staple")
    created = store.create_wallet("Cliente 1")

    assert created["address"].startswith("0x")
    assert len(created["address"]) == 42

    private_key = store.get_private_key(created["id"])
    recovered = Account.from_key(private_key)
    assert recovered.address == created["address"]

    store.close()

    reopened = WalletStore(db_path)
    reopened.unlock("correct horse battery staple")
    wallets = reopened.list_wallets()

    assert len(wallets) == 1
    assert wallets[0]["label"] == "Cliente 1"
    assert wallets[0]["address"] == created["address"]
    reopened.close()


def test_wrong_password_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "wallets.db"

    store = WalletStore(db_path)
    store.setup("a-strong-master-password")
    store.close()

    reopened = WalletStore(db_path)
    with pytest.raises(InvalidMasterPassword):
        reopened.unlock("wrong-password")
    reopened.close()

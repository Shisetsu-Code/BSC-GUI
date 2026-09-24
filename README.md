# BSC-GUI

Aplicación de escritorio para crear y administrar wallets de depósito compatibles con **BNB Smart Chain (BSC)**.

## Funciones

- Crea wallets EVM/BSC con entropía criptográficamente segura.
- Muestra dirección, etiqueta y fecha de creación.
- Abre la dirección seleccionada directamente en [BscScan](https://bscscan.com).
- Copia direcciones al portapapeles.
- Guarda las claves privadas **cifradas localmente** con una contraseña maestra.
- Permite revelar/copiar una clave privada únicamente desde la aplicación desbloqueada.
- No necesita RPC ni conexión blockchain para generar una dirección.

## Seguridad

La base local se crea en:

```text
data/wallets.db
```

`data/` está excluido del repositorio mediante `.gitignore`.

Las claves privadas se cifran con Fernet. La clave de cifrado se deriva de la contraseña maestra con PBKDF2-HMAC-SHA256 y un salt aleatorio local.

**Este proyecto es un MVP de escritorio.** Para custodia real de fondos de terceros o un PSP/PSAV, el signer debería migrarse a HSM/MPC o a un servicio de firma aislado. No uses GitHub, variables de CI ni archivos de texto para almacenar seeds o private keys de producción.

## Windows

La forma más rápida:

```bat
run.bat
```

El script crea `.venv`, instala las dependencias y abre la GUI.

Manual:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Linux

Tkinter puede requerir el paquete del sistema correspondiente:

```bash
sudo apt install python3-tk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## BscScan

Una dirección se abre como:

```text
https://bscscan.com/address/0x...
```

Una wallet recién creada puede aparecer sin actividad hasta que reciba su primera transacción. La dirección sigue siendo válida aunque todavía no tenga movimientos.

## Alcance actual

Esta versión **no envía fondos ni hace sweeps**. El siguiente módulo natural es agregar:

1. conexión RPC a BSC;
2. lectura de BNB y tokens BEP-20;
3. watcher de depósitos;
4. cola de retiros;
5. signer separado;
6. gestión automática de gas;
7. webhooks/API para integrarlo con el backend del PSP.

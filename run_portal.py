"""
Inicia o portal "Mural do Campus" (loopback, porta 5000).

Uso:
    python run_portal.py
Modo (padrão: vulneravel):
    Windows/PowerShell:  $env:LAB_MODE="corrigido"; python run_portal.py
    macOS/Linux:         LAB_MODE=corrigido python run_portal.py

Abra no navegador:  http://localhost:5000
"""
from portal.app import main

if __name__ == "__main__":
    main()

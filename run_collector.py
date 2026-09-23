"""
Inicia o coletor do laboratório (loopback, porta 9000).

Uso:
    python run_collector.py

Abra a página do atacante (opcional) em:  http://127.0.0.1:9000
O terminal deste processo é a evidência principal das capturas.
"""
from collector.collector import main

if __name__ == "__main__":
    main()

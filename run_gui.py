#!/usr/bin/env python3
"""
DaBlockChain GUI Launcher
GUI 버전 블록체인 애플리케이션 실행
"""
from crypto import SigningKey
from gui import main


if __name__ == "__main__":
    if SigningKey is None:
        print("This application requires the 'ecdsa' package.")
        print("Install with: python3 -m pip install ecdsa")
        exit(1)

    print("Starting DaBlockChain GUI...")
    main()

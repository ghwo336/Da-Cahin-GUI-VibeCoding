"""
daChain 메인 진입점
"""
from crypto import SigningKey
from cli import DaChainCLI


def main():
    """메인 함수"""
    if SigningKey is None:
        print("This demo requires the 'ecdsa' package.")
        print("Install with: python3 -m pip install ecdsa")
        return

    cli = DaChainCLI()
    cli.run()


if __name__ == "__main__":
    main()

"""Login não habilitado enquanto a política da plataforma impedir a coleta proposta."""
from src.bitdegree_access_policy import require_authorized_access


def main():
    try:
        require_authorized_access()
    except PermissionError:
        print('BitDegree: login e exportação de sessão não habilitados. '
              'Consulte VALIDATION_V23.md: bloqueio pelos termos da plataforma. '
              'Não forneça senha, cookies ou Secret para esta etapa.')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

# adicionar_usuario.py — Gerencia os usuários do sistema pelo terminal.
#
#   python adicionar_usuario.py adicionar          (pede e-mail e senha)
#   python adicionar_usuario.py listar
#   python adicionar_usuario.py remover --email fulano@gmail.com
#
# O e-mail é validado (formato + verificação de que o domínio existe e recebe e-mails).
# A senha é guardada como hash — ninguém consegue ler a senha original no banco.

import argparse
import getpass
import sys

from email_validator import validate_email, EmailNotValidError
from werkzeug.security import generate_password_hash

import database as db

TAMANHO_MINIMO_SENHA = 8


def validar_email(email, verificar_dominio=True):
    """Devolve o e-mail normalizado (minúsculo) ou levanta ValueError."""
    try:
        info = validate_email(email.strip(), check_deliverability=verificar_dominio)
    except EmailNotValidError as e:
        raise ValueError(f'E-mail inválido: {e}')
    return info.normalized.lower()


def cmd_adicionar(args):
    email = args.email or input('E-mail: ')
    try:
        email = validar_email(email, verificar_dominio=not args.sem_dns)
    except ValueError as e:
        print(e)
        return 1

    senha = args.senha
    if not senha:
        senha = getpass.getpass('Senha (não aparece enquanto digita): ')
        if senha != getpass.getpass('Repita a senha: '):
            print('As senhas não são iguais.')
            return 1
    if len(senha) < TAMANHO_MINIMO_SENHA:
        print(f'A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.')
        return 1

    db.init_db()
    if db.criar_usuario(email, generate_password_hash(senha)) is None:
        print(f'Já existe um usuário com o e-mail {email}.')
        return 1
    print(f'Usuário {email} criado com sucesso!')
    return 0


def cmd_listar(_args):
    db.init_db()
    usuarios = db.listar_usuarios()
    if not usuarios:
        print('Nenhum usuário cadastrado.')
    for u in usuarios:
        print(f"{u['id']:>3}  {u['email']:<40} criado em {u['criado_em']}")
    return 0


def cmd_remover(args):
    db.init_db()
    email = args.email.strip().lower()
    if db.remover_usuario(email):
        print(f'Usuário {email} removido.')
        return 0
    print('Usuário não encontrado.')
    return 1


def main():
    p = argparse.ArgumentParser(description='Gerenciar usuários da Calculateria')
    sub = p.add_subparsers(dest='comando', required=True)

    a = sub.add_parser('adicionar', help='cadastrar um novo usuário')
    a.add_argument('--email')
    a.add_argument('--senha', help='opcional; se omitida, será pedida de forma oculta')
    a.add_argument('--sem-dns', action='store_true',
                   help='não verifica se o domínio do e-mail existe (use só sem internet)')
    a.set_defaults(func=cmd_adicionar)

    l = sub.add_parser('listar', help='listar usuários')
    l.set_defaults(func=cmd_listar)

    r = sub.add_parser('remover', help='remover um usuário')
    r.add_argument('--email', required=True)
    r.set_defaults(func=cmd_remover)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == '__main__':
    main()

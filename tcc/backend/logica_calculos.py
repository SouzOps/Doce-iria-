# logica_calculos.py - Backend para cálculos de vendas de doces
# Funções para custo, lucro, % lucro e vendas totais

def calcular_lucro_unidade(custo, preco_venda):
    # MUDANÇA: a docstring foi fechada aqui, antes do código começar.
    # No original, o if e o return estavam DENTRO das aspas triplas,
    # sendo tratados como texto e nunca executados.
    """
    Calcula lucro por unidade de doce.

    :param custo: Custo de produção por unidade (R$)
    :param preco_venda: Preço de venda por unidade (R$)
    :return: Lucro por unidade (R$)
    """
    # MUDANÇA: if e return movidos para fora da docstring — agora são código de verdade.
    if custo <= 0 or preco_venda <= 0:
        raise ValueError("Custo e preço de venda devem ser > 0")
    return preco_venda - custo


def calcular_percentual_lucro(custo, preco_venda):
    # MUDANÇA: mesma correção — docstring fechada antes do código.
    # A chamada a calcular_lucro_unidade e o return estavam dentro das aspas.
    """
    Calcula % de lucro sobre o custo.

    :param custo: Custo por unidade (R$)
    :param preco_venda: Preço de venda por unidade (R$)
    :return: % lucro
    """
    # MUDANÇA: lógica movida para fora da docstring.
    lucro = calcular_lucro_unidade(custo, preco_venda)
    return (lucro / custo) * 100


def calcular_vendas_totais(custo, preco_venda, quantidade):
    # MUDANÇA: mesma correção — docstring fechada antes do código.
    # Todo o bloco if, os cálculos e o return dict estavam dentro das aspas.
    """
    Calcula totais de vendas.

    :param custo: Custo unitário
    :param preco_venda: Preço unitário
    :param quantidade: Qtd vendida
    :return: Dict com receita_total, custo_total, lucro_total, percentual_lucro
    """
    # MUDANÇA: validação e cálculos movidos para fora da docstring.
    if quantidade <= 0:
        raise ValueError("Quantidade deve ser > 0")

    receita_total = preco_venda * quantidade
    custo_total = custo * quantidade
    lucro_total = calcular_lucro_unidade(custo, preco_venda) * quantidade
    percentual = calcular_percentual_lucro(custo, preco_venda)
    return {
        'receita_total': receita_total,
        'custo_total': custo_total,
        'lucro_total': lucro_total,
        'percentual_lucro': percentual
    }


def calcular_preco_venda_markup(custo, markup_percent):
    # MUDANÇA: mesma correção — docstring fechada antes do código.
    # O if e o return estavam dentro das aspas e nunca eram executados.
    """
    Calcula preço de venda baseado em markup desejado.

    :param custo: Custo unitário
    :param markup_percent: % markup sobre custo
    :return: Preço de venda sugerido
    """
    # MUDANÇA: validação e cálculo movidos para fora da docstring.
    if markup_percent < 0:
        raise ValueError("Markup deve ser >= 0")
    return custo * (1 + markup_percent / 100)


def menu_calculadora():
    # MUDANÇA: o comentário com # foi convertido para docstring correta com aspas triplas.
    """Menu CLI interativo para testar cálculos."""
    print("=== Calculadora de Vendas de Doces ===")
    while True:
        # MUDANÇA: \\n corrigido para \n (no original havia barra dupla desnecessária).
        print("\n1. Lucro por unidade")
        print("2. % Lucro")
        print("3. Totais de vendas")
        print("4. Preço venda por markup")
        print("5. Sair")
        op = input("Escolha: ").strip()

        if op == '5':
            break

        elif op == '1':
            custo = float(input("Custo unitário (R$): "))
            pv = float(input("Preço venda (R$): "))
            print(f"Lucro unitário: R$ {calcular_lucro_unidade(custo, pv):.2f}")

        elif op == '2':
            custo = float(input("Custo unitário (R$): "))
            pv = float(input("Preço venda (R$): "))
            print(f"% Lucro: {calcular_percentual_lucro(custo, pv):.2f}%")

        elif op == '3':
            custo = float(input("Custo unitário (R$): "))
            pv = float(input("Preço venda (R$): "))
            qtd = float(input("Quantidade: "))
            res = calcular_vendas_totais(custo, pv, qtd)
            print(f"Receita total: R$ {res['receita_total']:.2f}")
            print(f"Custo total: R$ {res['custo_total']:.2f}")
            print(f"Lucro total: R$ {res['lucro_total']:.2f}")
            print(f"% Lucro: {res['percentual_lucro']:.2f}%")

        elif op == '4':
            custo = float(input("Custo unitário (R$): "))
            markup = float(input("% Markup desejado: "))
            pv = calcular_preco_venda_markup(custo, markup)
            print(f"Preço venda sugerido: R$ {pv:.2f}")


if __name__ == "__main__":
    menu_calculadora()

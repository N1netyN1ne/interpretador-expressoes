# Importação das bibliotecas necessárias
import gradio as gr
from transformers import pipeline
import re
from difflib import get_close_matches

# Carrega o modelo de transformação para gerar texto baseado em instruções
pipe = pipeline("text2text-generation", model="google/flan-t5-base")

# Dicionários para conversão de números por extenso
unidades = {
    "zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9
}

dezenas = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "quinze": 15,
    "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19,
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90
}

centenas = {
    "cem": 100, "cento": 100, "duzentos": 200, "trezentos": 300,
    "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600,
    "setecentos": 700, "oitocentos": 800, "novecentos": 900
}

multiplicadores = {
    "mil": 1_000,
    "milhão": 1_000_000, "milhões": 1_000_000,
    "bilhão": 1_000_000_000, "bilhões": 1_000_000_000,
    "trilhão": 1_000_000_000_000, "trilhões": 1_000_000_000_000
}

# Operadores matemáticos por extenso
operadores = {
    "mais": "+", "menos": "-", "vezes": "*",
    "multiplicado por": "*", "dividido por": "/",
    "divida": "/", "dividido": "/", "multiplique": "*",
    "subtraia": "-", "soma": "+"
}

# Função para converter números por extenso até trilhões
def converter_numero_extenso(texto):
    """
    Converte números escritos por extenso para seus equivalentes numéricos.

    Args:
        texto (str): Texto contendo números por extenso.

    Returns:
        str: Texto com números convertidos para dígitos.
    """
    tokens = texto.lower().split()
    total = 0
    parcial = 0
    resultado = []
    i = 0

    while i < len(tokens):
        palavra = tokens[i]
        if palavra in unidades:
            parcial += unidades[palavra]
        elif palavra in dezenas:
            parcial += dezenas[palavra]
        elif palavra in centenas:
            parcial += centenas[palavra]
        elif palavra == "e":
            pass
        elif palavra in multiplicadores:
            if parcial == 0:
                parcial = 1
            total += parcial * multiplicadores[palavra]
            parcial = 0
        elif palavra in operadores:
            if parcial > 0 or total > 0:
                resultado.append(str(total + parcial))
                parcial = 0
                total = 0
            resultado.append(operadores[palavra])
        else:
            if parcial > 0 or total > 0:
                resultado.append(str(total + parcial))
                parcial = 0
                total = 0
            resultado.append(palavra)
        i += 1

    if parcial > 0 or total > 0:
        resultado.append(str(total + parcial))

    return " ".join(resultado)

# Lista de palavras válidas para correção de erros de digitação
palavras_validas = list(unidades.keys()) + list(dezenas.keys()) + list(centenas.keys()) + list(multiplicadores.keys()) + list(operadores.keys())

# Correção de palavras com erro usando fuzzy matching
def corrigir_palavras(texto):
    """
    Corrige palavras com erros de digitação usando fuzzy matching.

    Args:
        texto (str): Texto contendo possíveis erros de digitação.

    Returns:
        str: Texto corrigido.
    """
    palavras = texto.lower().split()
    corrigidas = []
    for palavra in palavras:
        similares = get_close_matches(palavra, palavras_validas, n=1, cutoff=0.75)
        corrigidas.append(similares[0] if similares else palavra)
    return " ".join(corrigidas)

# Substituir operadores repetidos
def simplificar_operadores_repetidos(texto):
    """
    Remove operadores matemáticos repetidos desnecessariamente no texto.

    Args:
        texto (str): Expressão contendo operadores.

    Returns:
        str: Expressão simplificada.
    """
    texto = re.sub(r"\++", "+", texto)
    texto = re.sub(r"\-+", "-", texto)
    texto = re.sub(r"\*+", "*", texto)
    texto = re.sub(r"\/+", "/", texto)
    texto = re.sub(r"(\bmais\b\s+)+", "+", texto)
    texto = re.sub(r"(\bmenos\b\s+)+", "-", texto)
    texto = re.sub(r"(\bmais\b\s+\bmenos\b\s+)+", "-", texto)
    texto = re.sub(r"(\bmenos\b\s+\bmais\b\s+)+", "-", texto)
    return texto

# Pré-processamento final
def traduzir_expressao(texto):
    """
    Traduz uma expressão textual para uma expressão matemática pronta para avaliação.

    Args:
        texto (str): Texto escrito em linguagem natural.

    Returns:
        str: Expressão matemática formatada.
    """
    texto = texto.lower()
    texto = corrigir_palavras(texto)
    texto = converter_numero_extenso(texto)  # <- converte primeiro os números por extenso
    texto = simplificar_operadores_repetidos(texto)
    for palavra, simbolo in operadores.items():
        texto = re.sub(rf"\b{palavra}\b", simbolo, texto)
    return texto

# Função principal com explicação e formatação
def interpretar(expressao):
    """
    Processa uma expressão matemática em texto e gera o resultado calculado.

    Args:
        expressao (str): Expressão fornecida pelo usuário.

    Returns:
        str: Resultado final ou mensagem de erro.
    """
    try:
        if re.search(r"\d|\+|\-|\*|\/", expressao):
            texto_formatado = expressao
        else:
            texto_formatado = traduzir_expressao(expressao)

        prompt = f"Convert this sentence into a valid mathematical expression: {texto_formatado}"

        print(f"Prompt enviado ao modelo: {prompt}")  # Imprime o prompt antes de enviar
        saida = pipe(prompt, max_new_tokens=100, num_return_sequences=1)[0]['generated_text'].strip()
        print(f"Saída bruta do modelo: {saida}")  # Imprime a saída bruta


        # Limpa texto extra e deixa só a expressão
        saida_limpa = re.findall(r"[\d\+\-\*/\.\(\)\s]+", saida)
        saida_limpa = saida_limpa[0].strip() if saida_limpa else ""

        if not re.match(r"^[\d\+\-\*/\.\(\)\s]+$", saida_limpa):
            return f"Expressão inválida gerada: {saida}"

        # Avalia o resultado da expressão
        resultado = eval(saida_limpa)

        # Formata o resultado (número com vírgula para floats)
        if isinstance(resultado, float):
            resultado_formatado = f"{resultado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            resultado_formatado = f"{resultado:,}".replace(",", ".")

        return f"{saida_limpa} = {resultado_formatado}"

    except Exception as e:
        return f"Ocorreu um erro: {str(e)}"

# Interface Gradio
gr.Interface(
    fn=interpretar,
    inputs=gr.Textbox(label="Digite uma expressão (ex:Um mais cinco menos dois)"),
    outputs=gr.Textbox(label="Resultado Explicado"),
    title="Interpretador Didático de Expressões (Português)",
    description="Escreva contas com palavras ou números, incluindo operadores repetidos e erros de digitação. Ex: 'um mais mais mais mais menos 1'"
).launch()

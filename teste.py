import pandas as pd
import unicodedata

def remover_acentos(texto):
    """Remove acentos e força codificação ASCII pura, sem caracteres surpresa."""
    if pd.isna(texto):
        return ""
    texto = str(texto)
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def formatar_campo(valor, tamanho, tipo='texto'):
    """Trava o tamanho exato do campo, sem mais nem menos caracteres."""
    if tipo == 'texto':
        valor_limpo = remover_acentos(valor)
        # Alinha à esquerda com espaços e corta brutalmente se for maior
        return valor_limpo.ljust(tamanho)[:tamanho]
    elif tipo == 'numero':
        # Remove pontuações indesejadas e preenche com zeros à esquerda
        valor_limpo = ''.join(filter(str.isdigit, str(valor)))
        return valor_limpo.zfill(tamanho)[:tamanho]

def converter_csv_para_txt(arquivo_csv, arquivo_saida):
    df = pd.read_csv(arquivo_csv)
    linhas_txt = []

    # 1. Header (Exemplo do txt base com 28 posições)
    header = "1" + formatar_campo("007", 3, 'numero') + formatar_campo("23388544", 8, 'numero') + "2026010120260131"
    linhas_txt.append(header)

    # 2. Detalhes
    for _, row in df.iterrows():
        # Substitua as chaves pelos nomes exatos das colunas do seu CSV
        # e os números pelos tamanhos previstos no manual de integração.
        tipo = "2"
        # Exemplo de concatenação rígida:
        # num_nota = formatar_campo(row['numero_nota'], 8, 'numero')
        # ...
        # linha_detalhe = tipo + num_nota + inscricao + ...
        
        # linhas_txt.append(linha_detalhe)
        pass # Remova o pass e adicione os campos quando mapear as colunas

    # 3. Trailer
    trailer = "9" + formatar_campo(len(df) + 1, 7, 'numero')
    linhas_txt.append(trailer)

    # Salva o arquivo garantindo a quebra de linha padrão e sem linhas extras
    with open(arquivo_saida, 'w', encoding='ascii', newline='\r\n') as f:
        for linha in linhas_txt:
            f.write(linha + "\n")

# Execução
converter_csv_para_txt('NFSe_R_23388544_20260101_20260131_2.csv', 'saida_identica.txt')
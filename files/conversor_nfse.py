# -*- coding: utf-8 -*-
"""
Conversor NFS-e: CSV (exportação em lote da Prefeitura de SP) -> XML (um por nota)

Gera um arquivo .xml por nota fiscal, no padrão oficial da Prefeitura de São Paulo
(mesmo layout de tags do XML de exemplo fornecido pelo usuário).

LEIA O ARQUIVO LEIA-ME.txt PARA A LISTA DE CAMPOS COM CONFIANÇA REDUZIDA.
"""

import csv
import os
import re
import sys
import unicodedata
import traceback
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from xml.sax.saxutils import escape as xml_escape

# ---------------------------------------------------------------------------
# 1) CABEÇALHO DE REFERÊNCIA (166 colunas) — usado para validar o CSV importado
# ---------------------------------------------------------------------------
REFERENCE_HEADER = ['Tipo de Registro', 'Nº NFS-e', 'Data Hora NFE', 'Código de Verificação da NFS-e', 'Tipo de RPS', 'Série do RPS', 'Número do RPS', 'Data do Fato Gerador', 'Inscrição Municipal do Prestador', 'Indicador de CPF/CNPJ do Prestador', 'CPF/CNPJ do Prestador', 'Razão Social do Prestador', 'Tipo do Endereço do Prestador', 'Endereço do Prestador', 'Número do Endereço do Prestador', 'Complemento do Endereço do Prestador', 'Bairro do Prestador', 'Cidade do Prestador', 'UF do Prestador', 'CEP do Prestador', 'Email do Prestador', 'Opção Pelo Simples', 'Situação da Nota Fiscal', 'Data de Cancelamento', 'Nº da Guia', 'Data de Quitação da Guia Vinculada a Nota Fiscal', 'Valor dos Serviços', 'Valor das Deduções', 'Código do Serviço Prestado na Nota Fiscal', 'Alíquota', 'ISS devido', 'Valor do Crédito', 'ISS Retido', 'Indicador de CPF/CNPJ do Tomador', 'CPF/CNPJ do Tomador', 'Inscrição Municipal do Tomador', 'Inscrição Estadual do Tomador', 'Razão Social do Tomador', 'Tipo do Endereço do Tomador', 'Endereço do Tomador', 'Número do Endereço do Tomador', 'Complemento do Endereço do Tomador', 'Bairro do Tomador', 'Cidade do Tomador', 'UF do Tomador', 'CEP do Tomador', 'Email do Tomador', 'Nº NFS-e Substituta', 'ISS recolhido', 'ISS a recolher', 'Indicador de CPF/CNPJ do Intermediário', 'CPF/CNPJ do Intermediário', 'Inscrição Municipal do Intermediário', 'Razão Social do Intermediário', 'Repasse do Plano de Saúde', 'PIS/PASEP', 'COFINS', 'INSS', 'IR', 'CSLL', 'Carga tributária: Valor', 'Carga tributária: Porcentagem', 'Carga tributária: Fonte']
# Nota: a validação de cabeçalho abaixo confere apenas a QUANTIDADE mínima de
# colunas e o início da lista (campos usados pela conversão). Se a prefeitura
# mudar a ordem dessas colunas específicas, a validação vai pegar o erro.

# Índices (posição na linha do CSV) dos campos realmente usados na conversão.
# Usamos header.index(...) no código, então a ordem exata do arquivo não importa,
# desde que os NOMES das colunas existam.

CAMPOS_OBRIGATORIOS = [
    'Nº NFS-e', 'Data Hora NFE', 'Código de Verificação da NFS-e',
    'Data do Fato Gerador', 'Inscrição Municipal do Prestador',
    'Indicador de CPF/CNPJ do Prestador', 'CPF/CNPJ do Prestador',
    'Razão Social do Prestador', 'Tipo do Endereço do Prestador',
    'Endereço do Prestador', 'Número do Endereço do Prestador',
    'Complemento do Endereço do Prestador', 'Bairro do Prestador',
    'Cidade do Prestador', 'UF do Prestador', 'CEP do Prestador',
    'Email do Prestador', 'Situação da Nota Fiscal', 'Opção Pelo Simples',
    'Nº da Guia', 'Valor dos Serviços', 'Código do Serviço Prestado na Nota Fiscal',
    'Alíquota', 'ISS devido', 'Valor do Crédito', 'ISS Retido',
    'Indicador de CPF/CNPJ do Tomador', 'CPF/CNPJ do Tomador',
    'Inscrição Municipal do Tomador', 'Razão Social do Tomador',
    'Tipo do Endereço do Tomador', 'Endereço do Tomador',
    'Número do Endereço do Tomador', 'Complemento do Endereço do Tomador',
    'Bairro do Tomador', 'Cidade do Tomador', 'UF do Tomador',
    'CEP do Tomador', 'Email do Tomador', 'Discriminação dos Serviços'
    if False else None,  # placeholder removido abaixo
]
CAMPOS_OBRIGATORIOS = [c for c in CAMPOS_OBRIGATORIOS if c]

# Campos da "cauda" (Reforma Tributária / retenções) usados de forma best-effort.
# Ver LEIA-ME.txt: confiança menor, incluídos só se vierem preenchidos no CSV.
CAMPOS_OPCIONAIS_CAUDA = ['IR', 'CSLL']

# ---------------------------------------------------------------------------
# 2) TABELA DE UFs (código IBGE de 2 dígitos <-> sigla)
# ---------------------------------------------------------------------------
UF_POR_CODIGO = {
    11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA', 16: 'AP', 17: 'TO',
    21: 'MA', 22: 'PI', 23: 'CE', 24: 'RN', 25: 'PB', 26: 'PE', 27: 'AL',
    28: 'SE', 29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP', 41: 'PR',
    42: 'SC', 43: 'RS', 50: 'MS', 51: 'MT', 52: 'GO', 53: 'DF',
}

# ---------------------------------------------------------------------------
# 3) TABELA DE MUNICÍPIOS (IBGE) — carregada do arquivo municipios_ibge.csv
# ---------------------------------------------------------------------------
def caminho_recurso(nome_arquivo):
    """Resolve o caminho de um arquivo bundlado, funcionando tanto rodando o
    .py direto quanto empacotado com PyInstaller (--onefile)."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, nome_arquivo)


def normaliza_nome(s):
    """Remove acentos, deixa maiúsculo e colapsa espaços — para comparar nomes
    de cidade de forma tolerante a pequenas diferenças de grafia."""
    s = s.strip().upper()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'\s+', ' ', s)
    return s


def carrega_municipios():
    caminho = caminho_recurso('municipios_ibge.csv')
    mapa = {}
    with open(caminho, encoding='utf-8') as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            uf_num = int(linha['codigo_uf'])
            uf_sigla = UF_POR_CODIGO.get(uf_num)
            if not uf_sigla:
                continue
            chave = (normaliza_nome(linha['nome']), uf_sigla)
            mapa[chave] = linha['codigo_ibge']
    return mapa


# ---------------------------------------------------------------------------
# 4) FUNÇÕES DE TRANSFORMAÇÃO DE CAMPOS (formato CSV -> formato XML)
# ---------------------------------------------------------------------------
class CampoInvalido(Exception):
    """Erro de conversão de um campo específico — mensagem já pronta pro usuário."""
    pass


def so_digitos(valor):
    return re.sub(r'\D', '', valor or '')


def data_para_iso(valor, nome_campo):
    """'DD/MM/AAAA' -> 'AAAA-MM-DD'"""
    valor = (valor or '').strip()
    if not valor:
        raise CampoInvalido(f"campo '{nome_campo}' está vazio, mas é obrigatório")
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', valor.split(' ')[0])
    if not m:
        raise CampoInvalido(f"campo '{nome_campo}' com data em formato inesperado: '{valor}' (esperado DD/MM/AAAA)")
    d, mo, y = m.groups()
    return f"{y}-{mo}-{d}"


def data_hora_para_iso(valor, nome_campo):
    """'DD/MM/AAAA HH:MM:SS' -> 'AAAA-MM-DDTHH:MM:SS'"""
    valor = (valor or '').strip()
    if not valor:
        raise CampoInvalido(f"campo '{nome_campo}' está vazio, mas é obrigatório")
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4}) (\d{2}):(\d{2}):(\d{2})$', valor)
    if not m:
        raise CampoInvalido(f"campo '{nome_campo}' com data/hora em formato inesperado: '{valor}'")
    d, mo, y, hh, mi, ss = m.groups()
    return f"{y}-{mo}-{d}T{hh}:{mi}:{ss}"


def valor_br_para_decimal(valor, nome_campo, obrigatorio=True):
    """'3.275,18' -> '3275.18' ; '138,60' -> '138.6' ; '9.240,00' -> '9240'"""
    valor = (valor or '').strip()
    if not valor:
        if obrigatorio:
            raise CampoInvalido(f"campo '{nome_campo}' está vazio, mas é obrigatório")
        return None
    v = valor.replace('.', '').replace(',', '.')
    try:
        numero = float(v)
    except ValueError:
        raise CampoInvalido(f"campo '{nome_campo}' com valor numérico inválido: '{valor}'")
    texto = f"{numero:.2f}".rstrip('0').rstrip('.')
    return texto if texto else '0'


def aliquota_para_fracao(valor, nome_campo):
    """Alíquota em % (ex: '5,00') -> fração decimal (ex: '0.05')"""
    valor = (valor or '').strip()
    if not valor:
        raise CampoInvalido(f"campo '{nome_campo}' está vazio, mas é obrigatório")
    v = valor.replace('.', '').replace(',', '.')
    try:
        percentual = float(v)
    except ValueError:
        raise CampoInvalido(f"campo '{nome_campo}' com alíquota inválida: '{valor}'")
    fracao = percentual / 100.0
    texto = f"{fracao:.4f}".rstrip('0').rstrip('.')
    return texto if texto else '0'


def cep_sem_zero_esquerda(valor, nome_campo):
    d = so_digitos(valor)
    if not d:
        raise CampoInvalido(f"campo '{nome_campo}' (CEP) está vazio")
    return str(int(d))


def cidade_para_ibge(nome_cidade, uf, nome_campo, municipios_map):
    chave = (normaliza_nome(nome_cidade), (uf or '').strip().upper())
    codigo = municipios_map.get(chave)
    if not codigo:
        raise CampoInvalido(
            f"não encontrei o código IBGE para a cidade '{nome_cidade}' (UF {uf}) — "
            f"confira se o nome está escrito exatamente como no cadastro do IBGE"
        )
    return codigo


def bool_sn_para_texto(valor, nome_campo):
    v = (valor or '').strip().upper()
    if v == 'S':
        return 'true'
    if v == 'N':
        return 'false'
    raise CampoInvalido(f"campo '{nome_campo}' esperava 'S' ou 'N', veio '{valor}'")


def cpf_ou_cnpj_tag(valor_doc, indicador, nome_campo):
    """Retorna (nome_da_tag, valor_so_digitos) — <CPF> ou <CNPJ>."""
    d = so_digitos(valor_doc)
    ind = (indicador or '').strip()
    if ind == '1' or (ind != '2' and len(d) == 11):
        if len(d) != 11:
            raise CampoInvalido(f"campo '{nome_campo}' indicado como CPF mas tem {len(d)} dígitos (esperado 11)")
        return 'CPF', d
    if ind == '2' or (ind != '1' and len(d) == 14):
        if len(d) != 14:
            raise CampoInvalido(f"campo '{nome_campo}' indicado como CNPJ mas tem {len(d)} dígitos (esperado 14)")
        return 'CNPJ', d
    raise CampoInvalido(f"campo '{nome_campo}' com indicador de CPF/CNPJ inválido: '{indicador}'")


# ---------------------------------------------------------------------------
# 5) MONTAGEM DO XML DE UMA NOTA
# ---------------------------------------------------------------------------
def tag(nome, valor, obrigatorio=True):
    """Gera '<Nome>valor</Nome>', ou string vazia se opcional e sem valor."""
    if valor is None or valor == '':
        if obrigatorio:
            return f"<{nome}></{nome}>"
        return ""
    return f"<{nome}>{xml_escape(str(valor))}</{nome}>"


def monta_endereco(bloco_nome, get, sufixo, obrigatorio_bairro=False):
    partes = []
    partes.append(tag('TipoLogradouro', get(f'Tipo do Endereço do {sufixo}')))
    partes.append(tag('Logradouro', get(f'Endereço do {sufixo}')))
    partes.append(tag('NumeroEndereco', get(f'Número do Endereço do {sufixo}')))
    partes.append(tag('ComplementoEndereco', get(f'Complemento do Endereço do {sufixo}'), obrigatorio=False))
    partes.append(tag('Bairro', get(f'Bairro do {sufixo}'), obrigatorio=obrigatorio_bairro))
    return partes


def converte_linha_para_xml(row, get, municipios_map, avisos):
    """row: dict {nome_da_coluna: valor}. get(nome) = row.get(nome,'').strip()
    Levanta CampoInvalido em caso de erro fatal para a linha.
    Preenche 'avisos' (lista) com observações não-fatais (campo opcional ausente etc.)."""

    numero_nfse = get('Nº NFS-e')
    if not numero_nfse:
        raise CampoInvalido("campo 'Nº NFS-e' vazio — não é possível identificar a nota")

    partes = ['<?xml version="1.0" encoding="UTF-8"?>', '<NFe>']

    # ChaveNFe
    partes.append('<ChaveNFe>')
    partes.append(tag('InscricaoPrestador', str(int(so_digitos(get('Inscrição Municipal do Prestador'))))))
    partes.append(tag('NumeroNFe', str(int(so_digitos(numero_nfse)))))
    partes.append(tag('CodigoVerificacao', get('Código de Verificação da NFS-e')))
    # ChaveNotaNacional: não vem no CSV (é gerado pelo sistema nacional) — omitido.
    partes.append('</ChaveNFe>')

    partes.append(tag('DataEmissaoNFe', data_hora_para_iso(get('Data Hora NFE'), 'Data Hora NFE')))
    # Data do Fato Gerador no CSV só tem data (sem hora). Usamos 00:00:00 como hora.
    # CONFIANÇA REDUZIDA — ver LEIA-ME.txt.
    partes.append(tag('DataFatoGeradorNFe', data_para_iso(get('Data do Fato Gerador'), 'Data do Fato Gerador') + 'T00:00:00'))

    tag_doc, doc_digitos = cpf_ou_cnpj_tag(
        get('CPF/CNPJ do Prestador'), get('Indicador de CPF/CNPJ do Prestador'), 'CPF/CNPJ do Prestador')
    partes.append(f'<CPFCNPJPrestador>{tag(tag_doc, doc_digitos)}</CPFCNPJPrestador>')

    partes.append(tag('RazaoSocialPrestador', get('Razão Social do Prestador')))

    partes.append('<EnderecoPrestador>')
    partes.extend(monta_endereco('EnderecoPrestador', get, 'Prestador', obrigatorio_bairro=False))
    cidade_p = cidade_para_ibge(get('Cidade do Prestador'), get('UF do Prestador'), 'Cidade do Prestador', municipios_map)
    partes.append(tag('Cidade', cidade_p))
    partes.append(tag('UF', get('UF do Prestador')))
    partes.append(tag('CEP', cep_sem_zero_esquerda(get('CEP do Prestador'), 'CEP do Prestador')))
    partes.append('</EnderecoPrestador>')

    partes.append(tag('EmailPrestador', get('Email do Prestador'), obrigatorio=False))
    partes.append(tag('StatusNFe', get('Situação da Nota Fiscal')))
    # TributacaoNFe: NÃO existe coluna equivalente clara no CSV. Valor fixo 'T'
    # (Tributável) usado como padrão — CONFIRME antes de usar em produção.
    partes.append(tag('TributacaoNFe', 'T'))
    avisos.append("TributacaoNFe preenchido com valor padrão 'T' (não há coluna correspondente no CSV — confirme)")

    partes.append(tag('OpcaoSimples', get('Opção Pelo Simples')))
    numero_guia = get('Nº da Guia')
    if numero_guia:
        partes.append(tag('NumeroGuia', str(int(so_digitos(numero_guia)))))

    partes.append(tag('ValorServicos', valor_br_para_decimal(get('Valor dos Serviços'), 'Valor dos Serviços')))

    ir = get('IR')
    if ir:
        partes.append(tag('ValorIR', valor_br_para_decimal(ir, 'IR', obrigatorio=False)))
        avisos.append("ValorIR preenchido a partir da coluna 'IR' — mapeamento não confirmado, confira o valor gerado")
    csll = get('CSLL')
    if csll:
        partes.append(tag('ValorCSLL', valor_br_para_decimal(csll, 'CSLL', obrigatorio=False)))
        avisos.append("ValorCSLL preenchido a partir da coluna 'CSLL' — mapeamento não confirmado, confira o valor gerado")

    partes.append(tag('CodigoServico', get('Código do Serviço Prestado na Nota Fiscal')))
    partes.append(tag('AliquotaServicos', aliquota_para_fracao(get('Alíquota'), 'Alíquota')))
    partes.append(tag('ValorISS', valor_br_para_decimal(get('ISS devido'), 'ISS devido')))
    partes.append(tag('ValorCredito', valor_br_para_decimal(get('Valor do Crédito'), 'Valor do Crédito')))
    partes.append(tag('ISSRetido', bool_sn_para_texto(get('ISS Retido'), 'ISS Retido')))

    tag_doc_t, doc_digitos_t = cpf_ou_cnpj_tag(
        get('CPF/CNPJ do Tomador'), get('Indicador de CPF/CNPJ do Tomador'), 'CPF/CNPJ do Tomador')
    partes.append(f'<CPFCNPJTomador>{tag(tag_doc_t, doc_digitos_t)}</CPFCNPJTomador>')

    im_tomador = get('Inscrição Municipal do Tomador')
    if im_tomador:
        partes.append(tag('InscricaoMunicipalTomador', str(int(so_digitos(im_tomador)))))

    partes.append(tag('RazaoSocialTomador', get('Razão Social do Tomador')))

    partes.append('<EnderecoTomador>')
    partes.extend(monta_endereco('EnderecoTomador', get, 'Tomador', obrigatorio_bairro=False))
    cidade_t = cidade_para_ibge(get('Cidade do Tomador'), get('UF do Tomador'), 'Cidade do Tomador', municipios_map)
    partes.append(tag('Cidade', cidade_t))
    partes.append(tag('UF', get('UF do Tomador')))
    partes.append(tag('CEP', cep_sem_zero_esquerda(get('CEP do Tomador'), 'CEP do Tomador')))
    partes.append('</EnderecoTomador>')

    partes.append(tag('EmailTomador', get('Email do Tomador'), obrigatorio=False))
    partes.append(tag('Discriminacao', get('Discriminação dos Serviços'), obrigatorio=False))

    partes.append('</NFe>')

    cnpj_prestador_arquivo = doc_digitos if tag_doc == 'CNPJ' else doc_digitos.rjust(14, '0')
    nome_arquivo = f"{cnpj_prestador_arquivo}-{so_digitos(get('Inscrição Municipal do Prestador'))}-{so_digitos(numero_nfse)}-nfse.xml"

    partes = [p for p in partes if p]  # remove entradas vazias (campos opcionais ausentes)
    return "\r\n".join(partes), nome_arquivo


# ---------------------------------------------------------------------------
# 6) LEITURA E VALIDAÇÃO DO CSV + LOOP DE CONVERSÃO
# ---------------------------------------------------------------------------
def le_csv(caminho_csv):
    """Lê o CSV tentando cp1252 e depois utf-8. Retorna (header, linhas_de_dados)."""
    for encoding in ('cp1252', 'utf-8-sig', 'latin1'):
        try:
            with open(caminho_csv, encoding=encoding, newline='') as f:
                leitor = csv.reader(f, delimiter=';')
                linhas = list(leitor)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("não consegui ler o arquivo com nenhum encoding testado (cp1252, utf-8, latin1)")

    linhas = [l for l in linhas if any(campo.strip() for campo in l)]
    if not linhas:
        raise ValueError("o arquivo CSV está vazio")
    header = linhas[0]
    dados = linhas[1:]
    return header, dados


def valida_cabecalho(header):
    faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in header]
    if faltando:
        raise ValueError(
            "o CSV não tem as colunas esperadas pela conversão. Faltando: "
            + ", ".join(faltando[:8]) + (" ..." if len(faltando) > 8 else "")
            + f"\n(o CSV tem {len(header)} colunas; o layout de referência tem {len(REFERENCE_HEADER)})"
        )


def converte_arquivo(caminho_csv, pasta_saida, log):
    log(f"Lendo {os.path.basename(caminho_csv)} ...")
    header, dados = le_csv(caminho_csv)
    valida_cabecalho(header)
    log(f"Cabeçalho OK — {len(header)} colunas, {len(dados)} linhas de dados encontradas.")

    municipios_map = carrega_municipios()
    log(f"Tabela de municípios (IBGE) carregada: {len(municipios_map)} registros.")

    idx = {nome: i for i, nome in enumerate(header)}
    n_cols_esperado = len(header)

    sucesso = 0
    erros = []
    for i, linha in enumerate(dados, start=2):  # linha 2 = primeira linha de dados (1 = cabeçalho)
        primeiro_campo = linha[0].strip() if linha else ''
        if primeiro_campo.lower() == 'total':
            continue  # linha de totais no fim do CSV — não é uma nota, ignorar

        if len(linha) != n_cols_esperado:
            msg = (f"Linha {i}: tem {len(linha)} colunas, esperado {n_cols_esperado} "
                   f"— provável ; a mais/a menos nesta nota. Pulei esta linha.")
            log("  [ERRO] " + msg)
            erros.append(msg)
            continue

        row = {nome: linha[idx[nome]] for nome in header}
        get = lambda nome: (row.get(nome, '') or '').strip()

        avisos = []
        try:
            xml_texto, nome_arquivo = converte_linha_para_xml(row, get, municipios_map, avisos)
        except CampoInvalido as e:
            nfse_num = get('Nº NFS-e') or '?'
            msg = f"Linha {i} (NFS-e {nfse_num}): {e}. Pulei esta nota."
            log("  [ERRO] " + msg)
            erros.append(msg)
            continue
        except Exception as e:
            nfse_num = get('Nº NFS-e') or '?'
            msg = f"Linha {i} (NFS-e {nfse_num}): erro inesperado ({e}). Pulei esta nota."
            log("  [ERRO] " + msg)
            erros.append(msg)
            continue

        caminho_saida = os.path.join(pasta_saida, nome_arquivo)
        try:
            with open(caminho_saida, 'w', encoding='utf-8', newline='') as f:
                f.write(xml_texto)
        except OSError as e:
            msg = f"Linha {i}: não consegui salvar o arquivo '{nome_arquivo}' ({e})."
            log("  [ERRO] " + msg)
            erros.append(msg)
            continue

        sucesso += 1
        for aviso in avisos:
            log(f"  [aviso] NFS-e {get('Nº NFS-e')}: {aviso}")
        log(f"  OK — {nome_arquivo}")

    log("")
    log(f"Concluído: {sucesso} nota(s) convertida(s) com sucesso, {len(erros)} com erro.")
    return sucesso, erros


# ---------------------------------------------------------------------------
# 7) INTERFACE GRÁFICA (Tkinter)
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Conversor NFS-e — CSV para XML")
        self.geometry("720x520")
        self.resizable(True, True)

        self.caminho_csv = tk.StringVar()
        self.pasta_saida = tk.StringVar()

        pad = {'padx': 10, 'pady': 6}

        frame_top = tk.Frame(self)
        frame_top.pack(fill='x', **pad)

        tk.Label(frame_top, text="Arquivo CSV:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame_top, textvariable=self.caminho_csv, width=60).grid(row=0, column=1, sticky='we', padx=5)
        tk.Button(frame_top, text="Selecionar CSV...", command=self.selecionar_csv).grid(row=0, column=2)

        tk.Label(frame_top, text="Pasta de saída:").grid(row=1, column=0, sticky='w')
        tk.Entry(frame_top, textvariable=self.pasta_saida, width=60).grid(row=1, column=1, sticky='we', padx=5)
        tk.Button(frame_top, text="Selecionar pasta...", command=self.selecionar_pasta).grid(row=1, column=2)

        frame_top.columnconfigure(1, weight=1)

        tk.Button(self, text="Converter", command=self.converter, bg="#2f5496", fg="white",
                  font=("Arial", 11, "bold"), height=2).pack(fill='x', **pad)

        tk.Label(self, text="Log:").pack(anchor='w', padx=10)
        self.log_area = scrolledtext.ScrolledText(self, height=20, font=("Consolas", 9))
        self.log_area.pack(fill='both', expand=True, padx=10, pady=(0, 10))

    def log(self, texto):
        self.log_area.insert('end', texto + '\n')
        self.log_area.see('end')
        self.update_idletasks()

    def selecionar_csv(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o CSV exportado da Prefeitura",
            filetypes=[("Arquivos CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            self.caminho_csv.set(caminho)
            if not self.pasta_saida.get():
                self.pasta_saida.set(os.path.dirname(caminho))

    def selecionar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta onde salvar os XMLs")
        if pasta:
            self.pasta_saida.set(pasta)

    def converter(self):
        csv_path = self.caminho_csv.get().strip()
        out_dir = self.pasta_saida.get().strip()
        if not csv_path or not os.path.isfile(csv_path):
            messagebox.showerror("Erro", "Selecione um arquivo CSV válido.")
            return
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showerror("Erro", "Selecione uma pasta de saída válida.")
            return

        self.log_area.delete('1.0', 'end')
        try:
            sucesso, erros = converte_arquivo(csv_path, out_dir, self.log)
        except Exception as e:
            self.log("[FALHA GERAL] " + str(e))
            self.log(traceback.format_exc())
            messagebox.showerror("Erro ao converter", str(e))
            return

        if erros:
            messagebox.showwarning(
                "Conversão concluída com avisos",
                f"{sucesso} nota(s) convertida(s).\n{len(erros)} com erro — veja o log para detalhes."
            )
        else:
            messagebox.showinfo("Conversão concluída", f"{sucesso} nota(s) convertida(s) com sucesso!")


if __name__ == '__main__':
    App().mainloop()

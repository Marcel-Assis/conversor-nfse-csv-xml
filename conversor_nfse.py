import pandas as pd
import re
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- 1. FUNÇÕES DE FORMATAÇÃO ---

def formata_texto(valor, tamanho):
    if pd.isna(valor): valor = ""
    return str(valor).replace('\n', ' ').replace('\r', '').strip()[:tamanho].ljust(tamanho, ' ')

def formata_numero(valor, tamanho):
    if pd.isna(valor): return "0".zfill(tamanho)
    apenas_numeros = re.sub(r'\D', '', str(valor))[:tamanho]
    return apenas_numeros.zfill(tamanho)

def formata_moeda(valor, tamanho):
    if pd.isna(valor): return "0".zfill(tamanho)
    val_str = str(valor).strip()
    if ',' in val_str: val_str = val_str.replace('.', '').replace(',', '')
    elif '.' in val_str:
        partes = val_str.split('.')
        val_str = partes[0] + partes[1].ljust(2, '0')[:2]
    else: val_str += "00"
    return re.sub(r'\D', '', val_str).zfill(tamanho)

def formata_data(valor, tipo="curta"):
    if pd.isna(valor): return "0" * (8 if tipo == "curta" else 14)
    numeros = re.sub(r'\D', '', str(valor))
    if len(numeros) >= 8:
        data_fmt = f"{numeros[4:8]}{numeros[2:4]}{numeros[0:2]}"
        if tipo == "longa" and len(numeros) >= 14:
            return f"{data_fmt}{numeros[8:14]}"
        return data_fmt.ljust(8, '0')
    return "0" * (8 if tipo == "curta" else 14)

# --- 2. MOTOR DE CONVERSÃO ---

def processar_arquivo(csv_path, txt_path):
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='cp1252', dtype=str)
        
        # Filtro: Mantém apenas as linhas reais de nota fiscal
        if 'Tipo de Registro' in df.columns:
            df = df[df['Tipo de Registro'].astype(str).str.strip() == '2']
        else:
            df = df[df['Nº NFS-e'].notna()]
        
        linhas_txt = []
        linhas_txt.append("1007233885442026010120260131")
        
        # O Gabarito oficial: zeros exatos para evitar buracos nos valores não preenchidos
        gabarito_linha_2 = "21372946720260102010449WNLLSNAIRPS  0000600000119934520260101000010925139260.975.174/0001-00ASSOCIACAO DE BENEFICENCIA E FILANTROPIA SAO CRISTOVAO                     R  AMERICO VENTURA                                   123                                     ALTO DA MOOCA                 São Paulo                                         SP03128020setorfiscal@saocristovao.com.br                                            0M000000000000000000000000000000000000032751800000000000000002097050000000000016375000000000000000N200.485.325/0001-01000023388544000000000000M.CARDOSO ASSESSORIA CONTABIL LTDA                                         R  CELSO DE AZEVEDO MARQUES                          15                                      PARQUE DA MOOCA               São Paulo                                         SP03122010                                                                                   0000000000000000000000000000003                  000000000000                                                                                          00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000          0000000000000000000000000000000                              0000000000000000000000000                                                                                                                                                 000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  000000      - -  -                                                                                                                                000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           NN                                        00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000                                                                                                                                                                                                                                                 REF SERVICO DE ASSISTENCIA MEDICA/PLANO DE SAUDE *** VALOR APROXIMADO DOS TRIBUTOS (ISENTO): R$0,00 - 01/01/2026"
        
        def inserir_dado(linha_base_lista, valor, inicio, tamanho, tipo="texto"):
            if tipo == "numero":
                val_fmt = formata_numero(valor, tamanho)
            elif tipo == "moeda":
                val_fmt = formata_moeda(valor, tamanho)
            elif tipo == "data_longa":
                val_fmt = formata_data(valor, 'longa')
            elif tipo == "data_curta":
                val_fmt = formata_data(valor, 'curta')
            else:
                val_fmt = formata_texto(valor, tamanho)
                
            linha_base_lista[inicio:inicio+tamanho] = list(val_fmt)

        for _, row in df.iterrows():
            linha_base = list(gabarito_linha_2)
            
            inserir_dado(linha_base, "2", 0, 1, "texto")
            inserir_dado(linha_base, row.get('Nº NFS-e', ''), 1, 8, "numero")
            inserir_dado(linha_base, row.get('Data Hora NFE', ''), 9, 14, "data_longa")
            inserir_dado(linha_base, row.get('Código de Verificação da NFS-e', ''), 23, 8, "texto")
            inserir_dado(linha_base, row.get('Tipo de RPS', ''), 31, 5, "texto")
            inserir_dado(linha_base, row.get('Série do RPS', ''), 36, 5, "texto")
            inserir_dado(linha_base, row.get('Número do RPS', ''), 41, 12, "numero")
            inserir_dado(linha_base, row.get('Data do Fato Gerador', ''), 53, 8, "data_curta")
            
            # PRESTADOR
            inserir_dado(linha_base, row.get('Inscrição Municipal do Prestador', ''), 61, 12, "numero") 
            inserir_dado(linha_base, row.get('Indicador de CPF/CNPJ do Prestador', ''), 73, 1, "numero")
            inserir_dado(linha_base, row.get('CPF/CNPJ do Prestador', ''), 74, 18, "texto")
            inserir_dado(linha_base, row.get('Razão Social do Prestador', ''), 92, 75, "texto")
            inserir_dado(linha_base, row.get('Tipo do Endereço do Prestador', ''), 167, 3, "texto")
            inserir_dado(linha_base, row.get('Endereço do Prestador', ''), 170, 50, "texto")
            inserir_dado(linha_base, row.get('Número do Endereço do Prestador', ''), 220, 10, "texto")
            inserir_dado(linha_base, row.get('Complemento do Endereço do Prestador', ''), 230, 30, "texto")
            inserir_dado(linha_base, row.get('Bairro do Prestador', ''), 260, 30, "texto")
            inserir_dado(linha_base, row.get('Cidade do Prestador', ''), 290, 50, "texto")
            inserir_dado(linha_base, row.get('UF do Prestador', ''), 340, 2, "texto")
            inserir_dado(linha_base, row.get('CEP do Prestador', ''), 342, 8, "numero")
            inserir_dado(linha_base, row.get('Email do Prestador', ''), 350, 75, "texto")
            inserir_dado(linha_base, row.get('Opção Pelo Simples', ''), 425, 1, "numero")
            inserir_dado(linha_base, row.get('Situação da Nota Fiscal', ''), 426, 1, "texto")
            
            # DATAS (Guias e Cancelamentos) - Ajustados para tipo numérico
            inserir_dado(linha_base, row.get('Data de Cancelamento', ''), 427, 8, "numero") 
            inserir_dado(linha_base, row.get('Nº da Guia', ''), 435, 12, "numero")
            inserir_dado(linha_base, row.get('Data de Quitação da Guia Vinculada a Nota Fiscal', ''), 447, 8, "numero")
            
            # VALORES GERAIS
            inserir_dado(linha_base, row.get('Valor dos Serviços', ''), 455, 15, "moeda")
            inserir_dado(linha_base, row.get('Valor das Deduções', ''), 470, 15, "moeda")
            inserir_dado(linha_base, row.get('Código do Serviço Prestado na Nota Fiscal', ''), 485, 5, "numero")
            
            val_aliquota = str(row.get('Alíquota', ''))
            inserir_dado(linha_base, val_aliquota.replace(',',''), 490, 4, "numero")
            
            inserir_dado(linha_base, row.get('ISS devido', ''), 494, 15, "moeda")
            # CORREÇÃO CRÍTICA: Valor do Crédito tem 14 posições!
            inserir_dado(linha_base, row.get('Valor do Crédito', ''), 509, 14, "moeda")
            inserir_dado(linha_base, row.get('ISS Retido', ''), 523, 1, "texto")

            # TOMADOR
            inserir_dado(linha_base, row.get('Indicador de CPF/CNPJ do Tomador', ''), 524, 1, "numero")
            inserir_dado(linha_base, row.get('CPF/CNPJ do Tomador', ''), 525, 18, "texto")
            inserir_dado(linha_base, row.get('Inscrição Municipal do Tomador', ''), 543, 12, "numero")
            inserir_dado(linha_base, row.get('Inscrição Estadual do Tomador', ''), 555, 12, "numero")
            inserir_dado(linha_base, row.get('Razão Social do Tomador', ''), 567, 75, "texto")
            inserir_dado(linha_base, row.get('Tipo do Endereço do Tomador', ''), 642, 3, "texto")
            inserir_dado(linha_base, row.get('Endereço do Tomador', ''), 645, 50, "texto")
            inserir_dado(linha_base, row.get('Número do Endereço do Tomador', ''), 695, 10, "texto")
            inserir_dado(linha_base, row.get('Complemento do Endereço do Tomador', ''), 705, 30, "texto")
            inserir_dado(linha_base, row.get('Bairro do Tomador', ''), 735, 30, "texto")
            inserir_dado(linha_base, row.get('Cidade do Tomador', ''), 765, 50, "texto")
            inserir_dado(linha_base, row.get('UF do Tomador', ''), 815, 2, "texto")
            inserir_dado(linha_base, row.get('CEP do Tomador', ''), 817, 8, "numero")
            
            inserir_dado(linha_base, row.get('ISS recolhido', ''), 919, 15, "moeda")

            # IMPOSTOS RETIDOS
            inserir_dado(linha_base, row.get('PIS/PASEP', ''), 1072, 15, "moeda")
            inserir_dado(linha_base, row.get('COFINS', ''), 1087, 15, "moeda")
            inserir_dado(linha_base, row.get('INSS', ''), 1102, 15, "moeda")
            inserir_dado(linha_base, row.get('IR', ''), 1117, 15, "moeda")
            inserir_dado(linha_base, row.get('CSLL', ''), 1132, 15, "moeda")

            # ADQUIRENTE / DESTINATÁRIO
            inserir_dado(linha_base, row.get('Adquirente CNPJ', ''), 1948, 18, "texto")
            inserir_dado(linha_base, row.get('Adquirente Razão Social', ''), 2007, 75, "texto")
            inserir_dado(linha_base, row.get('Adquirente Logradouro', ''), 2157, 50, "texto")
            inserir_dado(linha_base, row.get('Adquirente Bairro', ''), 2207, 30, "texto")
            inserir_dado(linha_base, row.get('Adquirente Cidade', ''), 2237, 50, "texto")
            # O sistema exporta UF+CEP numa string única como "SP03122-010" na posição 2309
            uf = str(row.get('Adquirente UF', ''))
            cep = str(row.get('Adquirente CEP', ''))
            inserir_dado(linha_base, f"{uf}{cep}", 2309, 11, "texto")

            # OPERAÇÕES, TRIBUTAÇÕES E CÓDIGOS NBS
            inserir_dado(linha_base, row.get('Codigo Operacao', ''), 2453, 6, "numero")
            inserir_dado(linha_base, row.get('Local Prestação Serviço', ''), 2467, 26, "texto")
            inserir_dado(linha_base, row.get('NBS', ''), 2611, 9, "numero")
            
            base_calc = str(row.get('Base Calculo IBS/CBS', ''))
            inserir_dado(linha_base, base_calc.replace(',', '').replace('.', ''), 2659, 15, "numero")

            # DISCRIMINAÇÃO E FIM
            inserir_dado(linha_base, row.get('Discriminação dos Serviços', ''), 4938, 448, "texto")
            
            linhas_txt.append("".join(linha_base).rstrip())
            
        # 3. Rodapé
        qtd_notas = formata_numero(len(df), 7)
        linhas_txt.append(f"9{qtd_notas}")
        
        with open(txt_path, 'w', encoding='cp1252') as f:
            for linha in linhas_txt:
                f.write(linha + '\n')
                
        return True, "Arquivo convertido com sucesso!"
    except Exception as e:
        return False, f"Erro ao converter: {str(e)}"

# --- 3. INTERFACE GRÁFICA (GUI) ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Conversor NFS-e SP (CSV para TXT)")
        self.geometry("450x250")
        self.caminho_csv = ""

        self.lbl_titulo = ctk.CTkLabel(self, text="Conversor de Layout SP", font=("Arial", 18, "bold"))
        self.lbl_titulo.pack(pady=15)

        self.btn_importar = ctk.CTkButton(self, text="1. Importar CSV", command=self.importar_csv)
        self.btn_importar.pack(pady=10)

        self.lbl_arquivo = ctk.CTkLabel(self, text="Nenhum arquivo selecionado", text_color="gray")
        self.lbl_arquivo.pack(pady=5)

        self.btn_converter = ctk.CTkButton(self, text="2. Converter e Salvar", command=self.converter, state="disabled", fg_color="green", hover_color="darkgreen")
        self.btn_converter.pack(pady=15)

    def importar_csv(self):
        self.caminho_csv = filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv")])
        if self.caminho_csv:
            nome_arquivo = self.caminho_csv.split("/")[-1]
            self.lbl_arquivo.configure(text=f"Arquivo: {nome_arquivo}", text_color="white")
            self.btn_converter.configure(state="normal")

    def converter(self):
        if not self.caminho_csv: return
        
        caminho_salvar = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="NFSe_Convertida.txt",
            filetypes=[("Arquivo de Texto", "*.txt")]
        )
        
        if caminho_salvar:
            sucesso, msg = processar_arquivo(self.caminho_csv, caminho_salvar)
            if sucesso:
                messagebox.showinfo("Sucesso", msg)
            else:
                messagebox.showerror("Erro", msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()
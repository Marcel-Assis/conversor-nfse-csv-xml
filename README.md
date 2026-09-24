# Conversor NFS-e — CSV para XML

Programa em Python com interface gráfica (Tkinter) que converte o CSV de
exportação em lote de NFS-e da Prefeitura de São Paulo em arquivos XML
individuais, um por nota fiscal, no layout oficial da prefeitura.

## O que faz

- Lê o CSV exportado em lote pela Prefeitura de São Paulo
- Gera um `.xml` separado para cada nota fiscal, nomeado como
  `{CNPJ do prestador}-{Inscrição Municipal}-{Número da NFS-e}-nfse.xml`
- Converte automaticamente os formatos de campo (datas, valores
  monetários, CPF/CNPJ, cidade → código IBGE, etc.)
- Valida o arquivo antes de processar (colunas esperadas, contagem de
  campos por linha) e valida cada campo individualmente
- Se uma nota tiver algum problema, ela é **pulada e reportada no log**
  — o restante do arquivo continua sendo processado normalmente

## Como usar

### Direto com Python

```bash
python conversor_nfse.py
```

(Não há dependências externas — usa só a biblioteca padrão do Python.)

### Gerando um executável Windows (.exe)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --add-data "municipios_ibge.csv;." conversor_nfse.py
```

O executável final aparece em `dist/conversor_nfse.exe` — é o único
arquivo necessário para rodar em outro PC Windows, sem precisar instalar
Python.

## Estrutura do repositório

```
conversor_nfse.py       # programa principal (lógica + interface gráfica)
municipios_ibge.csv      # tabela de municípios do Brasil com código IBGE
                          # (fonte: IBGE, via github.com/kelvins/municipios-brasileiros)
LEIA-ME.txt              # notas técnicas detalhadas e limitações conhecidas
```

## Limitações conhecidas

Alguns campos do XML não têm uma coluna equivalente clara no CSV
exportado e são preenchidos por convenção/melhor esforço (o programa
avisa no log sempre que usa um deles):

- `TributacaoNFe` — sem coluna correspondente no CSV, usa valor fixo `"T"`
- `ValorIR` / `ValorCSLL` — mapeados das colunas de retenções federais,
  formato validado mas sem exemplo oficial 100% confirmado
- `DataFatoGeradorNFe` — o CSV só traz a data (sem hora); a hora é
  preenchida com `00:00:00`
- `ChaveNotaNacional` — não é gerada (é criada pelo sistema nacional de
  NFS-e no momento da emissão); a tag é omitida do XML

Ver `LEIA-ME.txt` para mais detalhes.

## Licença

Uso pessoal / livre para adaptar.

import pandas as pd
import streamlit as st
from datetime import datetime
import unicodedata

st.set_page_config(page_title="Comparador de Preços", layout="centered")
st.image("LOGO QUITANDARIA (1).png", width=100)
st.title("🛒Corretor de Preços Tipo 3")

st.markdown("""
### ℹ️ Instruções:
1. Envie o arquivo `BANCO DE CÓDIGOS.xlsx`;
2. Envie o arquivo de comparação com os preços base do Tipo 03;
3. Envie os **três arquivos CSV** das lojas 6 (Caruaru), 14 (Jatiúca) e 16 (Beira Mar);
   - 📸 Veja abaixo como gerar esses relatórios no sistema:
   - 👉 [Clique aqui para  gerar os Relatorios Varejo-Facil .csv](https://quitandaria.varejofacil.com/app/#/vf?r=%2FrelatorioPreco%2Findex&b=Venda,Relat%C3%B3rios%20pre%C3%A7o,Listagem%20de%20pre%C3%A7os)
""")

st.image("Capturar.jpg", caption="Exemplo de como gerar o relatório no sistema Quitandaria", use_container_width=True)

st.markdown("""
4. O app irá gerar um relatório com:
   - Diferenças de preços;
   - Itens com preço no Varejo, mas ausentes no Tipo 03.
""")

# Função para normalizar colunas
def normalizar_coluna(col):
    return unicodedata.normalize("NFKD", col).encode("ascii", errors="ignore").decode("utf-8").strip().lower()

# Upload do banco de códigos
df_BC = None
uploaded_banco = st.file_uploader("1. Envie o arquivo 'BANCO DE CÓDIGOS.xlsx'", type=["xlsx"])
if uploaded_banco:
    df_BC = pd.read_excel(uploaded_banco)
    st.success("Banco de códigos carregado com sucesso!")

# Upload do arquivo de comparação
df_merged = None
uploaded_comparacao = st.file_uploader("2. Envie o arquivo de comparação de preços (.xlsx)", type=["xlsx"])
if uploaded_comparacao:
    df = pd.read_excel(uploaded_comparacao, skiprows=2)
    df.columns = df.columns.str.strip()
    colunas_desejadas = ["Produto", "Descrição (Produto)", "Preço"]
    df_merged = df[colunas_desejadas]
    df_merged["Preço"] = (df_merged["Preço"] * 1.05).round(2)

    if df_BC is not None:
        df_merged = df_merged.merge(df_BC[["SANKHYA", "VAREJO"]], left_on="Produto", right_on="SANKHYA", how="left")
        df_merged.drop(columns=["SANKHYA"], inplace=True)
        df_merged.dropna(subset=["VAREJO"], inplace=True)
        df_merged["VAREJO"] = df_merged["VAREJO"].astype(int)
        st.success("Arquivo de comparação processado com sucesso!")

# Upload dos arquivos CSV das lojas
st.markdown("### 3. Envie os arquivos CSV das lojas 6, 14 e 16")

loja_6 = st.file_uploader("📄 Loja 6 - Caruaru", type=["csv"])
loja_14 = st.file_uploader("📄 Loja 14 - Jatiúca", type=["csv"])
loja_16 = st.file_uploader("📄 Loja 16 - Beira Mar", type=["csv"])

dfs = []
for arquivo, loja_nome in zip([loja_6, loja_14, loja_16], ["Loja 6", "Loja 14", "Loja 16"]):
    if arquivo:
        try:
            try:
                df_loja = pd.read_csv(arquivo, sep=";", encoding="utf-8")
            except UnicodeDecodeError:
                arquivo.seek(0)
                df_loja = pd.read_csv(arquivo, sep=";", encoding="ISO-8859-1")
            except pd.errors.EmptyDataError:
                st.warning(f"{loja_nome}: Arquivo vazio ou inválido.")
                continue

            if df_loja.empty or df_loja.columns.size == 0:
                st.warning(f"{loja_nome}: Arquivo sem colunas válidas.")
                continue

            # Normaliza e mapeia nomes de colunas
            df_loja.columns = [normalizar_coluna(col) for col in df_loja.columns]

            colunas_desejadas = {
                "cdigo do produto": "Código do Produto",
                "codigo do produto": "Código do Produto",
                "descrio do produto": "Descrição do Produto",
                "descricao do produto": "Descrição do Produto",
                "embalagem": "Embalagem",
                "venda atual": "Venda Atual"
            }

            colunas_presentes = set(df_loja.columns)
            colunas_necessarias = set(colunas_desejadas.keys())

            colunas_validas = colunas_necessarias.intersection(colunas_presentes)
            if len(colunas_validas) < 4:
                st.warning(f"{loja_nome}: Colunas esperadas não encontradas. Detectadas: {list(df_loja.columns)}")
                continue

            df_loja_filtrado = df_loja[list(colunas_validas)].copy()
            df_loja_filtrado.rename(columns={k: v for k, v in colunas_desejadas.items() if k in colunas_validas}, inplace=True)
            df_loja_filtrado["Loja"] = loja_nome
            dfs.append(df_loja_filtrado)

        except Exception as e:
            st.warning(f"Erro ao processar {loja_nome}: {e}")

Preco_atual = pd.concat(dfs, ignore_index=True) if dfs else None

# Geração do relatório final
df_diferentes = None
if st.button("4. Gerar Relatório de Diferenças"):
    if Preco_atual is not None and df_merged is not None:
        df_final = Preco_atual.merge(df_merged[["VAREJO", "Preço"]], left_on="Código do Produto", right_on="VAREJO", how="left")
        df_final.drop(columns=["VAREJO"], inplace=True, errors='ignore')
        df_final.dropna(subset=["Preço"], inplace=True)

        df_final["Venda Atual"] = df_final["Venda Atual"].astype(str).str.replace(',', '.').astype(float)
        df_final["Preço"] = df_final["Preço"].astype(float)

        df_diferentes = df_final[df_final["Venda Atual"].round(2) != df_final["Preço"].round(2)]
        df_diferentes = df_diferentes.drop(columns=["Loja"], errors='ignore')
        df_diferentes = df_diferentes.drop_duplicates(subset=["Código do Produto"])

        st.success("Relatório gerado com sucesso!")
        st.dataframe(df_diferentes)

        txt_content = "\n".join(
            f"{row['Código do Produto']};{row['Preço']:.2f}".replace('.', ',') for _, row in df_diferentes.iterrows()
        )

        st.download_button(
            label="📥 Baixar Precos_Diferentes.txt",
            data=txt_content,
            file_name="Precos_Diferentes.txt",
            mime="text/plain"
        )

        # Itens com preço no varejo mas ausentes no Tipo 03
        codigos_lojas = Preco_atual["Código do Produto"].astype(str).unique()
        codigos_tipo03 = df_merged["VAREJO"].astype(str).unique()
        codigos_faltantes = list(set(codigos_lojas) - set(codigos_tipo03))

        df_faltantes = Preco_atual[Preco_atual["Código do Produto"].astype(str).isin(codigos_faltantes)]
        df_faltantes = df_faltantes.drop_duplicates(subset=["Código do Produto"])

        if not df_faltantes.empty:
            st.markdown("### ⚠️ Itens com Preço no Varejo mas Ausentes no Tipo 03")
            st.dataframe(df_faltantes)

            csv_faltantes = df_faltantes.to_csv(index=False, sep=";", encoding="utf-8")
            st.download_button(
                label="📥 Baixar Itens_a_Revisar.csv",
                data=csv_faltantes,
                file_name="Itens_a_Revisar.csv",
                mime="text/csv"
            )

# Rodapé
st.markdown("""
---
**Desenvolvido por Victor Gama**  
*Analista de Compras*  
📞 (81) 99106-9698  
© 2025 Quitandaria. Todos os direitos reservados.
""")

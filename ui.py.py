import streamlit as st

def apply_executive_ui():
    """
    Injeta regras de CSS para transformar a interface do Streamlit em um Dashboard Executivo C-Level.
    """
    st.markdown("""
        <style>
            /* Importação de fonte moderna */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
            
            html, body, [class*="css"] {
                font-family: 'Inter', sans-serif;
            }
            
            /* Fundo principal da aplicação */
            .main {
                background-color: #F8FAFC;
            }
            
            /* Ocultar elementos desnecessários da barra superior */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Cabeçalho Executivo com sombra elegante */
            .exec-header-container {
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                padding: 24px 32px;
                border-radius: 16px;
                color: #FFFFFF;
                margin-bottom: 24px;
                box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
            }
            .exec-header-title {
                font-size: 26px;
                font-weight: 800;
                letter-spacing: -0.5px;
                margin: 0;
                color: #FFFFFF;
            }
            .exec-header-subtitle {
                font-size: 14px;
                color: #94A3B8;
                margin-top: 4px;
                font-weight: 400;
            }
            
            /* Cartões de KPI Executivos */
            .kpi-card {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 20px 24px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }
            .kpi-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.06);
            }
            
            .kpi-border-primary { border-left: 5px solid #0284C7; }
            .kpi-border-success { border-left: 5px solid #16A34A; }
            .kpi-border-warning { border-left: 5px solid #F59E0B; }
            .kpi-border-danger  { border-left: 5px solid #DC2626; }
            
            .kpi-label {
                font-size: 12px;
                font-weight: 700;
                color: #64748B;
                text-transform: uppercase;
                letter-spacing: 0.6px;
                margin-bottom: 8px;
            }
            .kpi-value {
                font-size: 32px;
                font-weight: 800;
                color: #0F172A;
                line-height: 1;
            }
            .kpi-footer {
                font-size: 12px;
                color: #64748B;
                margin-top: 8px;
                display: flex;
                align-items: center;
                gap: 4px;
            }

            /* Estilização das Tabs Executivas */
            .stTabs [data-baseweb="tab-list"] {
                gap: 8px;
                background-color: #F1F5F9;
                padding: 6px;
                border-radius: 12px;
            }
            .stTabs [data-baseweb="tab"] {
                height: 44px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                color: #64748B;
                padding: 0px 20px;
                border: none !important;
            }
            .stTabs [aria-selected="true"] {
                background-color: #FFFFFF !important;
                color: #0284C7 !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
        </style>
    """, unsafe_allow_html=True)

def render_executive_header(title: str, subtitle: str):
    """Renderiza um cabeçalho executivo elegante no topo da aplicação."""
    st.markdown(f"""
        <div class="exec-header-container">
            <div class="exec-header-title">{title}</div>
            <div class="exec-header-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

def render_kpi_card(title: str, value: str, footer: str = "", variant: str = "primary"):
    """
    Renderiza um card de KPI customizado com sombra e indicador lateral.
    Variants disponíveis: 'primary', 'success', 'warning', 'danger'
    """
    border_class = f"kpi-border-{variant}"
    st.markdown(f"""
        <div class="kpi-card {border_class}">
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-footer">{footer}</div>
        </div>
    """, unsafe_allow_html=True)
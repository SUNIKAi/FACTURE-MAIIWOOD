import io
import os
import os.path
import tempfile
from datetime import date
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
import locale
import json

# Configuration du format des nombres
locale.setlocale(locale.LC_ALL, '')

def format_number(number):
    return locale.format_string("%.2f", number, grouping=True)

def load_client_history():
    if os.path.exists('client_history.json'):
        with open('client_history.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'noms': [], 'entreprises': [], 'emails': []}

def save_client_history(client_data):
    history = load_client_history()
    if client_data['nom'] and client_data['nom'] not in history['noms']:
        history['noms'].append(client_data['nom'])
    if client_data['entreprise'] and client_data['entreprise'] not in history['entreprises']:
        history['entreprises'].append(client_data['entreprise'])
    if client_data['email'] and client_data['email'] not in history['emails']:
        history['emails'].append(client_data['email'])
    
    with open('client_history.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def save_invoice(data):
    if not os.path.exists('invoices.json'):
        invoices = []
    else:
        with open('invoices.json', 'r', encoding='utf-8') as f:
            invoices = json.load(f)
    
    data['date'] = date.today().strftime("%d/%m/%Y")
    invoices.append(data)
    
    with open('invoices.json', 'w', encoding='utf-8') as f:
        json.dump(invoices, f, ensure_ascii=False, indent=4)

def load_invoices():
    if os.path.exists('invoices.json'):
        with open('invoices.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def create_pdf(data, show_total=False):
    buffer = io.BytesIO()
    width, height = A4

    # Création du PDF
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # En-tête
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "INVOICE")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"N° {data['numero']}")
    c.drawString(450, height - 70, str(date.today().strftime("%d/%m/%Y")))

    # Informations BEVINGER
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "BEVINGER")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 140, "312 W 2nd St A4851,")
    c.drawString(50, height - 155, "Casper, Wyoming 82601 US")
    c.drawString(50, height - 170, "vincentfrenchwood@gmail.com")
    c.drawString(50, height - 185, "Tel:+66 93 429 02 08")

    # Informations client
    c.setFont("Helvetica-Bold", 12)
    x = 350
    y = height - 120
    text = "À destination de : " + data['client_nom'] if data['langue'] == 'Français' else "To: " + data['client_nom']
    text_width = c.stringWidth(text, "Helvetica-Bold", 12)
    c.drawString(x, y, text)
    c.line(x, y-2, x + text_width, y-2)
    
    # Centrage des informations client
    c.setFont("Helvetica", 10)
    entreprise_text = data['client_entreprise']
    email_text = data['client_email']
    
    x_entreprise = x + (text_width - c.stringWidth(entreprise_text, "Helvetica", 10)) / 2
    x_email = x + (text_width - c.stringWidth(email_text, "Helvetica", 10)) / 2
    
    c.drawString(x_entreprise, height - 135, entreprise_text)
    c.drawString(x_email, height - 150, email_text)

    # Tableau des services
    y = height - 300
    
    styles = getSampleStyleSheet()
    
    # En-têtes et largeurs des colonnes
    headers = ['Prestation', 'Prix/u', 'Quantité', 'Prix total'] if data['langue'] == 'Français' else ['Service', 'Unit price', 'Quantity', 'Total price']
    col_widths = [(width-100)*0.4, (width-100)*0.2, (width-100)*0.2, (width-100)*0.2]
    
    table_data = [headers]
    
    total_ht = 0
    # Données du tableau
    for service in data['services']:
        description = Paragraph(
            service['prestation'].replace('\n', '<br/>'),
            ParagraphStyle(
                'Normal',
                fontSize=10,
                leading=12,
                wordWrap='CJK'
            )
        )
        row = [
            description,
            f"{format_number(service['prix_unitaire'])} €",
            format_number(service['quantite']),
            f"{format_number(service['prix_total'])} €"
        ]
        table_data.append(row)
        total_ht += service['prix_total']
    
    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical en haut
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table_height = table.wrap(width - 100, height)[1]
    table.drawOn(c, 50, y - table_height)

    # Total avec double encadré
    if show_total:
        y_total = y - table_height - 30
        c.setFont("Helvetica-Bold", 12)
        total_text = "Total HT" if data['langue'] == 'Français' else "Total excl. tax"
        total_string = f"{total_text}: {format_number(total_ht)} €"
        
        text_width = c.stringWidth(total_string, "Helvetica-Bold", 12)
        padding = 10
        
        # Position x alignée avec la fin du tableau
        x_total = 50 + sum(col_widths) - text_width - (padding * 2)
        
        # Double cadre
        c.setLineWidth(0.5)
        c.rect(x_total, y_total - 5, text_width + (padding * 2), 20)
        c.setLineWidth(0.25)
        c.rect(x_total + 2, y_total - 3, text_width + (padding * 2) - 4, 16)
        
        # Texte du total
        c.drawString(x_total + padding, y_total, total_string)

    # Footer
    def add_footer(c):
        footer_translations = {
            'Français': {
                'terms_title': "Terms",
                'payment_title': "Paiement",
                'terms': [
                    "• Délaie de paiement 30 jours net facture",
                    "• Tout retard de paiement entraine l'exigibilité d'une indemnité",
                    "  forfaitaire pour frais de recouvrement de 40 euros.",
                    "• Intérêt de retard = montant impayé x taux d'intérêt x nombre",
                    "  de jours de retard / 365"
                ],
                'payment_table': [
                    ("Nom", "BEVINGER LLC"),
                    ("IBAN", "BE37 9050 7778 6428"),
                    ("BIC CODE", "TRWIBEB1XXX"),
                    ("Location", "Brussels Belgium")
                ]
            },
            'English': {
                'terms_title': "Terms",
                'payment_title': "Payment",
                'terms': [
                    "• Payment due within 30 days from invoice date",
                    "• Any late payment will result in a fixed compensation",
                    "  for recovery costs of 40 euros.",
                    "• Late payment interest = unpaid amount x interest rate x",
                    "  number of days late / 365"
                ],
                'payment_table': [
                    ("Name", "BEVINGER LLC"),
                    ("IBAN", "BE37 9050 7778 6428"),
                    ("BIC CODE", "TRWIBEB1XXX"),
                    ("Location", "Brussels Belgium")
                ]
            }
        }
        
        translations = footer_translations[data['langue']]
        
        c.saveState()
        footer_y = 190
        
        # Calculer les hauteurs pour l'alignement
        terms_height = len(translations['terms']) * 15
        
        # Ligne de séparation
        c.line(50, footer_y, width-50, footer_y)
        
        # Section Terms (gauche)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, footer_y - 20, translations['terms_title'])
        c.setFont("Helvetica", 8)
        
        for i, term in enumerate(translations['terms']):
            c.drawString(50, footer_y - 40 - (i * 15), term)
        
        # Section Paiement (droite)
        payment_y = footer_y - 40  # Aligné avec le début du texte des terms
        c.setFont("Helvetica-Bold", 10)
        x_payment = width/2
        c.drawString(x_payment, footer_y - 20, translations['payment_title'])
        
        # Tableau de paiement
        payment_data = translations['payment_table']
        table_width = 248
        row_height = 20
        col_width = table_width / 2
        
        # Fond gris clair pour le tableau
        c.setFillColor(colors.Color(0.95, 0.95, 0.95))
        c.rect(x_payment, payment_y - (len(payment_data) * row_height),
               table_width, len(payment_data) * row_height, fill=1)
        c.setFillColor(colors.black)
        
        # Cadre et contenu du tableau
        c.rect(x_payment, payment_y - (len(payment_data) * row_height),
               table_width, len(payment_data) * row_height)
        
        c.setFont("Helvetica", 8)
        for i, (label, value) in enumerate(payment_data):
            y = payment_y - (i * row_height)
            if i > 0:
                c.line(x_payment, y, x_payment + table_width, y)
            c.drawString(x_payment + 5, y - 15, label)
            c.drawString(x_payment + col_width + 5, y - 15, value)
        
        c.line(x_payment + col_width, payment_y - (len(payment_data) * row_height),
               x_payment + col_width, payment_y)
        
        c.restoreState()
    
    add_footer(c)
    
    c.save()
    buffer.seek(0)
    return buffer

def main():
    st.title("Générateur de Factures")

    # Initialisation de la session state
    if 'current_data' not in st.session_state:
        st.session_state.current_data = {
            'numero': "001",
            'client_nom': "",
            'client_entreprise': "",
            'client_email': "",
            'services': []
        }
    
    # Boutons en haut de l'interface
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Reset"):
            st.session_state.current_data = {
                'numero': "001",
                'client_nom': "",
                'client_entreprise': "",
                'client_email': "",
                'services': []
            }
            st.session_state.services = []
            st.rerun()

    with col2:
        if st.button("Historique"):
            st.session_state.show_history = True
            
    with col3:
        langue = st.selectbox("Langue / Language", ["Français", "English"])
    
    # Affichage de l'historique
    if 'show_history' in st.session_state and st.session_state.show_history:
        invoices = load_invoices()
        if invoices:
            selected_invoice = st.selectbox(
                "Sélectionner une facture",
                options=invoices,
                format_func=lambda x: f"Facture {x['numero']} - {x['client_nom']} - {x.get('date', 'N/A')}"
            )
            if selected_invoice and st.button("Charger cette facture"):
                st.session_state.current_data = selected_invoice
                st.session_state.services = selected_invoice['services']
                st.session_state.show_history = False
                st.rerun()
        else:
            st.info("Aucune facture dans l'historique")
            if st.button("Fermer l'historique"):
                st.session_state.show_history = False
                st.rerun()

    # Textes traduits
    texts = {
        "Français": {
            "numero": "Numéro invoice",
            "titre": "Titre de la facture",
            "client": "Informations client",
            "nom": "Nom du client",
            "entreprise": "Entreprise du client",
            "email": "Email du client",
            "prestation": "Prestation",
            "prix_unitaire": "Prix/u",
            "quantite": "Quantité",
            "prix_total": "Prix total",
            "ajouter": "Ajouter un service",
            "total_ht": "Afficher le total HT",
            "generer": "Générer la facture",
            "telecharger": "Télécharger la facture"
        },
        "English": {
            "numero": "Invoice number",
            "titre": "Invoice title",
            "client": "Client information",
            "nom": "Client name",
            "entreprise": "Company",
            "email": "Email",
            "prestation": "Service",
            "prix_unitaire": "Unit price",
            "quantite": "Quantity",
            "prix_total": "Total price",
            "ajouter": "Add service",
            "total_ht": "Show total without tax",
            "generer": "Generate invoice",
            "telecharger": "Download invoice"
        }
    }
    t = texts[langue]

    # Formulaire principal
    st.header(t["client"])
    
    # Chargement de l'historique des clients
    client_history = load_client_history()
    
    numero = st.text_input(t["numero"], value=st.session_state.current_data['numero'])
    
    # Champs client avec suggestions
    client_nom = st.text_input(
        t["nom"],
        value=st.session_state.current_data['client_nom'],
        key="client_nom"
    )
    if client_nom == "":  # Afficher les suggestions uniquement si le champ est vide
        nom_suggestion = st.selectbox(
            "Suggestions noms précédents",
            options=[""] + client_history['noms'],
            key="nom_suggestion"
        )
        if nom_suggestion:
            st.session_state.current_data['client_nom'] = nom_suggestion
            st.rerun()

    client_entreprise = st.text_input(
        t["entreprise"],
        value=st.session_state.current_data['client_entreprise'],
        key="client_entreprise"
    )
    if client_entreprise == "":
        entreprise_suggestion = st.selectbox(
            "Suggestions entreprises précédentes",
            options=[""] + client_history['entreprises'],
            key="entreprise_suggestion"
        )
        if entreprise_suggestion:
            st.session_state.current_data['client_entreprise'] = entreprise_suggestion
            st.rerun()

    client_email = st.text_input(
        t["email"],
        value=st.session_state.current_data['client_email'],
        key="client_email"
    )
    if client_email == "":
        email_suggestion = st.selectbox(
            "Suggestions emails précédents",
            options=[""] + client_history['emails'],
            key="email_suggestion"
        )
        if email_suggestion:
            st.session_state.current_data['client_email'] = email_suggestion
            st.rerun()
    
    # Section des prestations
    st.header("Services")
    
    # Liste pour stocker les services
    if 'services' not in st.session_state:
        st.session_state.services = []
    
    # Fonction pour calculer le prix total
    def calculate_total(prix, quantite):
        return float(prix) * float(quantite)
    
    # Ajouter un service
    if st.button(t["ajouter"]):
        st.session_state.services.append({
            "prestation": "",
            "prix_unitaire": 0.0,
            "quantite": 1.0,
            "prix_total": 0.0
        })
    
    # Conteneur pour les services
    services_container = st.container()
    
    # Afficher et modifier les services
    for idx, service in enumerate(st.session_state.services):
        with services_container:
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])
            
            with col1:
                service['prestation'] = st.text_area(
                    t["prestation"], 
                    value=service['prestation'], 
                    key=f"presta_{idx}",
                    height=100,
                    max_chars=200
                )
            with col2:
                service['prix_unitaire'] = st.number_input(
                    t["prix_unitaire"], 
                    value=float(service['prix_unitaire']),
                    min_value=0.0,
                    step=0.01,
                    key=f"prix_{idx}"
                )
            with col3:
                service['quantite'] = st.number_input(
                    t["quantite"], 
                    value=float(service['quantite']),
                    min_value=1.0,
                    step=1.0,
                    key=f"qte_{idx}"
                )
            with col4:
                service['prix_total'] = calculate_total(
                    service['prix_unitaire'], 
                    service['quantite']
                )
                st.text(f"{format_number(service['prix_total'])} €")
            with col5:
                if st.button("❌", key=f"del_{idx}"):
                    st.session_state.services.pop(idx)
                    st.rerun()
    
    # Option pour afficher le total HT
    show_total = st.checkbox(t["total_ht"])
    
    if show_total and st.session_state.services:
        total_ht = sum(service['prix_total'] for service in st.session_state.services)
        st.subheader(f"Total HT: {format_number(total_ht)} €")

    # Génération du PDF
    if st.button(t["generer"]):
        data = {
            'numero': numero,
            'client_nom': client_nom,
            'client_entreprise': client_entreprise,
            'client_email': client_email,
            'services': st.session_state.services,
            'langue': langue
        }
        
        # Sauvegarder les données client pour l'historique
        save_client_history({
            'nom': client_nom,
            'entreprise': client_entreprise,
            'email': client_email
        })
        
        # Sauvegarder la facture
        save_invoice(data)
        
        pdf_buffer = create_pdf(data, show_total=show_total)
        st.success("Facture générée avec succès !")
        st.download_button(
            label=t["telecharger"],
            data=pdf_buffer,
            file_name=f"facture_{numero}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()
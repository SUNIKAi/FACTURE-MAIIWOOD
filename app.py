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
    c.drawString(50, height - 50, "FACTURE")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"N° {data['numero']}")
    c.drawString(450, height - 70, str(date.today().strftime("%d/%m/%Y")))

    # Informations MAIIWOODATELIER
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "MAIIWOODATELIER")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 140, "521 route du port d'Arciat")
    c.drawString(50, height - 155, "Creche sur Saône 71680")
    c.drawString(50, height - 170, "quentin.bergeron71@gmail.com")
    c.drawString(50, height - 185, "Tel: 0622037204")
    c.drawString(50, height - 200, "SIRET: 93356216700017")

    # Informations client
    c.setFont("Helvetica-Bold", 12)
    x = 350
    y = height - 120
    text = "À destination de : " + data['client_nom'] 
    text_width = c.stringWidth(text, "Helvetica-Bold", 12)
    c.drawString(x, y, text)
    c.line(x, y-2, x + text_width, y-2)
    
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
    headers = ['Description', 'Prix/u', 'Quantité', 'Prix total']
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
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ])
    table.setStyle(style)

    table.wrapOn(c, width, height)
    table_height = table.wrap(width - 100, height)[1]
    table.drawOn(c, 50, y - table_height)
    
    # Bon pour accord (à gauche)
    y_accord = y - table_height - 50
    c.setFont("Helvetica-Bold", 9)
    
    # Double encadré pour bon pour accord
    accord_width = 200
    accord_height = 80
    c.rect(50, y_accord - accord_height, accord_width, accord_height)
    c.rect(52, y_accord - accord_height + 2, accord_width - 4, accord_height - 4)
    
    # Texte du bon pour accord
    c.drawString(60, y_accord - 20, "Bon pour accord :")
    c.drawString(60, y_accord - 40, "Date :")
    c.drawString(60, y_accord - 60, "Signature :")

    # Double encadré pour les totaux (à droite)
    totals_width = 200
    totals_height = 80
    x_totals = width - 50 - totals_width
    
    c.rect(x_totals, y_accord - totals_height, totals_width, totals_height)
    c.rect(x_totals + 2, y_accord - totals_height + 2, totals_width - 4, totals_height - 4)
    
    # Lignes horizontales pour séparer les totaux
    c.line(x_totals + 2, y_accord - 20, x_totals + totals_width - 2, y_accord - 20)
    c.line(x_totals + 2, y_accord - 40, x_totals + totals_width - 2, y_accord - 40)
    c.line(x_totals + 2, y_accord - 60, x_totals + totals_width - 2, y_accord - 60)
    
    # Texte des totaux
    c.drawString(x_totals + 10, y_accord - 15, f"Total HT: {format_number(total_ht)} €")
    c.drawString(x_totals + 10, y_accord - 35, "Remise: 0,00 €")
    c.drawString(x_totals + 10, y_accord - 55, "TVA: 0,00%")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_totals + 10, y_accord - 75, f"Total TTC: {format_number(total_ht)} €")

    # Ligne de séparation
    y_sep = y_accord - totals_height - 30
    c.line(50, y_sep, width-50, y_sep)

    # Bas de page
    y_footer = y_sep - 30

    # Section Livraison
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_footer, "Livraison")
    c.line(50, y_footer - 2, 100, y_footer - 2)  # Soulignement
    
    # Contenu livraison
    c.setFont("Helvetica", 9)
    if data.get('mode_livraison') == 'enlevement':
        c.drawString(50, y_footer - 20, "Enlèvement à :")
        c.drawString(50, y_footer - 35, "521 route du port d'Arciat")
        c.drawString(50, y_footer - 50, "Creche sur Saône 71680")
    else:
        c.drawString(50, y_footer - 20, "Adresse :")
        c.drawString(50, y_footer - 35, data.get('adresse_livraison', ''))

    # Terms
    c.setFont("Helvetica-Bold", 10)
    y_terms = y_footer - 80
    c.drawString(50, y_terms, "Terms")
    c.line(50, y_terms - 2, 85, y_terms - 2)  # Soulignement
    
    c.setFont("Helvetica", 9)
    c.drawString(50, y_terms - 20, "* Condition de réglement paiement complet")
    c.drawString(50, y_terms - 35, "  à livraison ou enlèvement du produit")
    c.drawString(50, y_terms - 55, "* Accompte de 30% pour réservation")
    c.drawString(50, y_terms - 70, "  avant livraison ou enlèvement ultérieur")

    # Section Paiement
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width/2, y_footer, "Paiement:")
    c.line(width/2, y_footer - 2, width/2 + 60, y_footer - 2)  # Soulignement

    # Tableau de paiement
    payment_data = [
        ['Banque', 'Indicatif', 'N° compte', 'Clé RIB', 'Domiciliation'],
        ['12135', '300', '4195188867', '14', 'MACON EUROPE'],
        ['IBAN:', 'FR76 1213 5003 0004 1951 8886 714', '', '', ''],
        ['BIC:', 'CEPAFRPP213', '', '', ''],
        ['Nom:', 'Bergeron Quentin', '', '', '']
    ]

    col_widths = [40, 40, 80, 30, 58]  # Largeurs des colonnes
    y_payment = y_footer - 20
    x_payment = width/2

    # Fond gris clair pour le tableau
    c.setFillColor(colors.Color(0.95, 0.95, 0.95))
    c.rect(x_payment, y_payment - 125, sum(col_widths), 125, fill=1)
    c.setFillColor(colors.black)

    # Dessiner le tableau
    c.setFont("Helvetica", 8)
    
    # Lignes horizontales
    for i in range(6):
        y = y_payment - (i * 25)
        c.line(x_payment, y, x_payment + sum(col_widths), y)

    # Lignes verticales pour les deux premières lignes
    x_current = x_payment
    for width in col_widths:
        if x_current == x_payment:  # Première colonne
            c.line(x_current, y_payment, x_current, y_payment - 125)
        else:
            c.line(x_current, y_payment, x_current, y_payment - 50)
        x_current += width
    c.line(x_payment + sum(col_widths), y_payment, x_payment + sum(col_widths), y_payment - 125)

    # Remplir le contenu
    for row_idx, row in enumerate(payment_data):
        y = y_payment - 17 - (row_idx * 25)
        x = x_payment
        for col_idx, cell in enumerate(row):
            if row_idx <= 1:  # Deux premières lignes
                c.drawString(x + 5, y, cell)
                x += col_widths[col_idx]
            else:  # Lignes avec fusion
                if col_idx == 0:
                    c.drawString(x + 5, y, cell)
                elif col_idx == 1:
                    c.drawString(x + 5, y, row[1])
                    break


    # Mentions légales
    y_mentions = y_terms - 100
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_mentions, "Mention légale")
    c.line(50, y_mentions - 2, 130, y_mentions - 2)  # Soulignement

    # Mentions légales
    y_mentions = y_terms - 100
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_mentions, "Mention légale")
    c.line(50, y_mentions - 2, 130, y_mentions - 2)  # Soulignement

    c.setFont("Helvetica", 7)
    mentions_text = [
        "*Garantie légale de conformité : Les produits vendus bénéficient d'une garantie légale de conformité de 2 ans à compter de la livraison,",
        "conformément aux articles L.217-3 et suivants du Code de la consommation.",
        "*Garantie contre les vices cachés : Les produits sont également couverts par une garantie contre les vices cachés pendant 2 ans à compter",
        "de la découverte du défaut (articles 1641 et suivants du Code civil).",
        "Pour toute question ou réclamation, veuillez contacter notre service client : 0622037204"
    ]
    
    for idx, line in enumerate(mentions_text):
        c.drawString(50, y_mentions - 20 - (idx * 10), line)

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
            'services': [],
            'mode_livraison': 'enlevement',
            'adresse_livraison': ""
        }
    
    # Boutons en haut de l'interface
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset"):
            st.session_state.current_data = {
                'numero': "001",
                'client_nom': "",
                'client_entreprise': "",
                'client_email': "",
                'services': [],
                'mode_livraison': 'enlevement',
                'adresse_livraison': ""
            }
            st.session_state.services = []
            st.rerun()

    with col2:
        if st.button("Historique"):
            st.session_state.show_history = True
            
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

    # Formulaire principal
    st.header("Informations client")
    
    # Chargement de l'historique des clients
    client_history = load_client_history()
    
    numero = st.text_input("Numéro facture", value=st.session_state.current_data['numero'])
    
    # Champs client avec suggestions
    client_nom = st.text_input(
        "Nom du client",
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
        "Entreprise du client",
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
        "Email du client",
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

    # Section livraison
    st.header("Mode de livraison")
    mode_livraison = st.radio(
        "Choisir le mode de livraison",
        ['enlevement', 'livraison'],
        key="mode_livraison",
        horizontal=True,
        index=0 if st.session_state.current_data['mode_livraison'] == 'enlevement' else 1
    )
    
    if mode_livraison == 'livraison':
        adresse_livraison = st.text_area(
            "Adresse de livraison",
            value=st.session_state.current_data['adresse_livraison'],
            key="adresse_livraison"
        )
    
    # Section des prestations
    st.header("Services")
    
    # Liste pour stocker les services
    if 'services' not in st.session_state:
        st.session_state.services = []
    
    # Fonction pour calculer le prix total
    def calculate_total(prix, quantite):
        return float(prix) * float(quantite)
    
    # Ajouter un service
    if st.button("Ajouter un service"):
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
                    "Description", 
                    value=service['prestation'], 
                    key=f"presta_{idx}",
                    height=100,
                    max_chars=200
                )
            with col2:
                service['prix_unitaire'] = st.number_input(
                    "Prix/u", 
                    value=float(service['prix_unitaire']),
                    min_value=0.0,
                    step=0.01,
                    key=f"prix_{idx}"
                )
            with col3:
                service['quantite'] = st.number_input(
                    "Quantité", 
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
    show_total = st.checkbox("Afficher le total HT")
    
    if show_total and st.session_state.services:
        total_ht = sum(service['prix_total'] for service in st.session_state.services)
        st.subheader(f"Total HT: {format_number(total_ht)} €")

    # Génération du PDF
    if st.button("Générer la facture"):
        data = {
            'numero': numero,
            'client_nom': client_nom,
            'client_entreprise': client_entreprise,
            'client_email': client_email,
            'services': st.session_state.services,
            'mode_livraison': mode_livraison,
            'adresse_livraison': adresse_livraison if mode_livraison == 'livraison' else ""
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
            label="Télécharger la facture",
            data=pdf_buffer,
            file_name=f"facture_{numero}.pdf",
            mime="application/pdf"
        )

if __name__ == "__main__":
    main()

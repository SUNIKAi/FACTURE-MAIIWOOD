import io
import os
import os.path
import tempfile
from datetime import date
import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
import locale
import json
from PIL import Image as PILImage
from io import BytesIO

# Configuration du format des nombres
locale.setlocale(locale.LC_ALL, '')

def format_number(number):
    return locale.format_string("%.2f", number, grouping=True)

def load_invoices():
    if os.path.exists('invoices.json'):
        with open('invoices.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_image(uploaded_file):
    if uploaded_file is not None:
        # Créer un dossier pour les images s'il n'existe pas
        os.makedirs('product_images', exist_ok=True)
        
        # Ouvrir et redimensionner l'image
        image = PILImage.open(uploaded_file)
        
        # Calculer les dimensions pour maintenir le ratio
        max_size = (200, 200)
        image.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        # Sauvegarder l'image
        file_path = os.path.join('product_images', uploaded_file.name)
        image.save(file_path)
        return file_path
    return None

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

def delete_invoice(invoice_number):
    if os.path.exists('invoices.json'):
        with open('invoices.json', 'r', encoding='utf-8') as f:
            invoices = json.load(f)
        
        invoices = [inv for inv in invoices if inv['numero'] != invoice_number]
        
        with open('invoices.json', 'w', encoding='utf-8') as f:
            json.dump(invoices, f, ensure_ascii=False, indent=4)
        return True
    return False

def create_pdf(data, total_ttc=None):
    buffer = io.BytesIO()
    width, height = A4

    # Création du PDF avec titre personnalisé
    title = f"Facture - {data['numero']} - {data['client_nom']}"
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(title)
    c.setAuthor('MAIIWOODATELIER')
    c.setSubject('Facture')
    c.setCreator('MAIIWOODATELIER')

    def dessiner_en_tete():
        # ... (votre code existant)

    def dessiner_bon_pour_accord_et_totaux(y_accord):
        # ... (votre code existant)

    def dessiner_bas_de_page(y_start):
        # ... (votre code existant)

    # Dessiner l'en-tête
    dessiner_en_tete()

    # Position initiale pour le tableau
    y = height - 250

    # Création du tableau
    styles = getSampleStyleSheet()

    # Vérifier si des photos sont présentes
    has_photos = any(
        service.get('image_path') and os.path.exists(service['image_path']) 
        for service in data['services']
    )

    # Ajuster les en-têtes et largeurs selon la présence de photos
    if has_photos:
        headers = ['Description', 'Photo', 'Prix/u', 'Quantité', 'Prix total']
        col_widths = [(width-100)*0.3, (width-100)*0.2, (width-100)*0.15, 
                    (width-100)*0.15, (width-100)*0.2]
    else:
        headers = ['Description', 'Prix/u', 'Quantité', 'Prix total']
        col_widths = [(width-100)*0.4, (width-100)*0.2, (width-100)*0.2, 
                    (width-100)*0.2]

    table_data = [headers]
    total_ht = 0
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
        
        row = [description]
        if has_photos:
            if service.get('image_path') and os.path.exists(service['image_path']):
                try:
                    img = Image(service['image_path'])
                    max_width = col_widths[1] - 10
                    max_height = 100
                    ratio = min(max_width/img.drawWidth, max_height/img.drawHeight)
                    img.drawWidth *= ratio
                    img.drawHeight *= ratio
                    row.append(img)
                except:
                    row.append('')
            else:
                row.append('')
                
        row.extend([
            f"{format_number(service['prix_unitaire'])} €",
            format_number(service['quantite']),
            f"{format_number(service['prix_total'])} €"
        ])
        
        table_data.append(row)
        total_ht += service['prix_total']

    table = Table(table_data, colWidths=col_widths)
    style = TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ])
    table.setStyle(style)

    # Calculer les dimensions
    table.wrapOn(c, width, height)
    table_height = table.wrap(width - 100, height)[1]
    
    # Hauteur requise pour le bon pour accord et les totaux
    hauteur_bpa_totaux = 100  # environ
    
    # Hauteur requise pour le bas de page
    hauteur_bas_page = 250  # environ
    
    # Hauteur disponible sur la première page
    hauteur_disponible = y - hauteur_bas_page - 20  # marge de 20

    # Cas 1: Tout tient sur la première page
    if table_height + hauteur_bpa_totaux <= hauteur_disponible:
        # Dessiner le tableau
        table.drawOn(c, 50, y - table_height)
        
        # Dessiner bon pour accord et totaux
        y_accord = y - table_height - 20
        dessiner_bon_pour_accord_et_totaux(y_accord)
        
        # Dessiner le bas de page sur la même page
        dessiner_bas_de_page(y - table_height - hauteur_bpa_totaux - 20)
        
    # Cas 2: Le tableau tient mais pas les totaux/bpa
    elif table_height <= hauteur_disponible:
        # Dessiner le tableau sur la page 1
        table.drawOn(c, 50, y - table_height)
        
        # Nouvelle page pour bon pour accord, totaux et bas de page
        c.showPage()
        dessiner_en_tete()
        
        # Dessiner bon pour accord et totaux en haut de la page 2
        y_accord = height - 250
        dessiner_bon_pour_accord_et_totaux(y_accord)
        
        # Dessiner le bas de page
        dessiner_bas_de_page(y_accord - hauteur_bpa_totaux - 20)
        
    # Cas 3: Le tableau ne tient pas sur une seule page
    else:
        # Calculer combien de lignes peuvent tenir sur la première page
        hauteur_ligne_moyenne = table_height / len(table_data)
        lignes_premiere_page = max(2, int(hauteur_disponible / hauteur_ligne_moyenne))
        
        # Première partie du tableau
        table1_data = table_data[:lignes_premiere_page]
        table1 = Table(table1_data, colWidths=col_widths)
        table1.setStyle(style)
        table1.wrapOn(c, width, height)
        table1_height = table1.wrap(width - 100, height)[1]
        table1.drawOn(c, 50, y - table1_height)
        
        # Nouvelle page
        c.showPage()
        dessiner_en_tete()
        
        # Position pour la suite du tableau
        y = height - 250
        
        # Deuxième partie du tableau
        table2_data = table_data[lignes_premiere_page:]
        table2 = Table(table2_data, colWidths=col_widths)
        table2.setStyle(style)
        table2.wrapOn(c, width, height)
        table2_height = table2.wrap(width - 100, height)[1]
        
        # Vérifier si le reste du tableau + bpa/totaux tiennent sur la page 2
        hauteur_restante_page2 = y - hauteur_bas_page - 20
        if table2_height + hauteur_bpa_totaux <= hauteur_restante_page2:
            table2.drawOn(c, 50, y - table2_height)
            y_accord = y - table2_height - 20
            dessiner_bon_pour_accord_et_totaux(y_accord)
            dessiner_bas_de_page(y - table2_height - hauteur_bpa_totaux - 20)
        else:
            # Dessiner le reste du tableau
            table2.drawOn(c, 50, y - table2_height)
            
            # Nouvelle page pour bon pour accord, totaux et bas de page
            c.showPage()
            dessiner_en_tete()
            y_accord = height - 250
            dessiner_bon_pour_accord_et_totaux(y_accord)
            dessiner_bas_de_page(y_accord - hauteur_bpa_totaux - 20)

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
            'adresse_client': "",
            'telephone_client': "",
            'client_email': "",
            'services': [],
            'mode_livraison': 'enlevement',
            'adresse_livraison': "",
            'remise': 0.0
        }

    # Boutons en haut de l'interface
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reset"):
            st.session_state.current_data = {
                'numero': "001",
                'client_nom': "",
                'adresse_client': "",
                'telephone_client': "",
                'client_email': "",
                'services': [],
                'mode_livraison': 'enlevement',
                'adresse_livraison': "",
                'remise': 0.0
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
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Charger cette facture"):
                    st.session_state.current_data = selected_invoice
                    st.session_state.services = selected_invoice['services']
                    st.session_state.show_history = False
                    st.rerun()
            with col2:
                if st.button("Supprimer cette facture"):
                    if delete_invoice(selected_invoice['numero']):
                        st.success("Facture supprimée avec succès!")
                        st.rerun()
                    else:
                        st.error("Erreur lors de la suppression de la facture")
        else:
            st.info("Aucune facture dans l'historique")
            if st.button("Fermer l'historique"):
                st.session_state.show_history = False
                st.rerun()

    # Formulaire principal
    st.header("Informations client")
    
    numero = st.text_input("Numéro facture", value=st.session_state.current_data['numero'])
    client_nom = st.text_input("Nom du client", value=st.session_state.current_data['client_nom'])
    adresse_client = st.text_input("Adresse client", value=st.session_state.current_data['adresse_client'])
    telephone_client = st.text_input("Téléphone client", value=st.session_state.current_data['telephone_client'])
    client_email = st.text_input("Email client", value=st.session_state.current_data['client_email'])

    # Mode de livraison
    st.header("Mode de livraison")
    mode_livraison = st.radio(
        "Choisir le mode de livraison",
        ['enlevement', 'livraison'],
        horizontal=True,
        index=0 if st.session_state.current_data['mode_livraison'] == 'enlevement' else 1
    )

    if mode_livraison == 'livraison':
        adresse_livraison = st.text_area(
            "Adresse de livraison",
            value=st.session_state.current_data.get('adresse_livraison', '')
        )
    else:
        adresse_livraison = ""

    # Section produits
    st.header("Produits")
    
    if 'services' not in st.session_state:
        st.session_state.services = []
    
    if st.button("Ajouter un produit"):
        st.session_state.services.append({
            "prestation": "",
            "prix_unitaire": 0.0,
            "quantite": 1.0,
            "prix_total": 0.0,
            "image_path": None
        })
    
    # Affichage des produits avec photos
    for idx, service in enumerate(st.session_state.services):
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])
        with col1:
            service['prestation'] = st.text_area(
                "Description", 
                value=service['prestation'], 
                key=f"presta_{idx}",
                height=100
            )
            # Upload d'image sous la description
            uploaded_file = st.file_uploader(
                "Photo du produit",
                type=['png', 'jpg', 'jpeg'],
                key=f"photo_{idx}",
                help="Formats acceptés : PNG, JPG, JPEG"
            )
            if uploaded_file:
                st.image(uploaded_file, width=150)
                service['image_path'] = save_image(uploaded_file)
            elif service.get('image_path') and os.path.exists(service['image_path']):
                st.image(service['image_path'], width=150)
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
            service['prix_total'] = service['prix_unitaire'] * service['quantite']
            st.text(f"{format_number(service['prix_total'])} €")
        with col5:
            if st.button("❌", key=f"del_{idx}"):
                if service.get('image_path') and os.path.exists(service['image_path']):
                    os.remove(service['image_path'])
                st.session_state.services.pop(idx)
                st.rerun()

    # Calculs et affichage des totaux
    if st.session_state.services:
        total_ht = sum(service['prix_total'] for service in st.session_state.services)
        
        st.header("Totaux")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.text(f"Total HT: {format_number(total_ht)} €")
        
        with col2:
            remise = st.number_input(
                "Remise (€)", 
                value=float(st.session_state.current_data.get('remise', 0)),
                min_value=0.0,
                max_value=float(total_ht),
                step=0.01
            )
        
        with col3:
            st.text("TVA: 0,00%")
            total_ttc = total_ht - remise
            st.text(f"Total TTC: {format_number(total_ttc)} €")

        # Génération du PDF
        if st.button("Générer la facture"):
            data = {
                'numero': numero,
                'client_nom': client_nom,
                'adresse_client': adresse_client,
                'telephone_client': telephone_client,
                'client_email': client_email,
                'services': st.session_state.services,
                'mode_livraison': mode_livraison,
                'adresse_livraison': adresse_livraison,
                'remise': remise
            }
            
            # Sauvegarder la facture
            save_invoice(data)
            
            # Générer le PDF
            pdf_buffer = create_pdf(data, total_ttc)
            st.success("Facture générée avec succès !")
            
            # Nom de fichier personnalisé
            filename = f"Facture - {numero} - {client_nom}.pdf"
            st.download_button(
                label="Télécharger la facture",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()

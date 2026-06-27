import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from database import db
from models import User, Company, Item, BugReport
from datetime import datetime, timedelta
from sqlalchemy import inspect, text, or_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def migrate_schema():
    inspector = inspect(db.engine)
    if 'items' in inspector.get_table_names():
        item_cols = {c['name'] for c in inspector.get_columns('items')}
        if 'refresh_requested_at' not in item_cols:
            db.session.execute(text('ALTER TABLE items ADD COLUMN refresh_requested_at DATETIME'))
    if 'bug_reports' in inspector.get_table_names():
        bug_cols = {c['name'] for c in inspector.get_columns('bug_reports')}
        if 'report_type' not in bug_cols:
            db.session.execute(text("ALTER TABLE bug_reports ADD COLUMN report_type VARCHAR(20) DEFAULT 'manual'"))
        if 'item_id' not in bug_cols:
            db.session.execute(text('ALTER TABLE bug_reports ADD COLUMN item_id INTEGER REFERENCES items(id)'))
        db.session.execute(text("UPDATE bug_reports SET report_type = 'manual' WHERE report_type IS NULL OR report_type = ''"))
        db.session.execute(text("UPDATE bug_reports SET report_type = 'expiration' WHERE title LIKE 'Solicitação de Renovação:%'"))
        backfill_refresh_item_ids()
    db.session.commit()

def refresh_request_title(item_title):
    return f"Solicitação de Renovação: {item_title}"

def backfill_refresh_item_ids():
    reports = BugReport.query.filter(
        BugReport.report_type == 'expiration',
        BugReport.item_id.is_(None)
    ).all()
    for report in reports:
        prefix = 'Solicitação de Renovação: '
        if not report.title.startswith(prefix):
            continue
        link_title = report.title[len(prefix):]
        item = Item.query.filter_by(company_id=report.company_id, title=link_title, type='link').first()
        if item:
            report.item_id = item.id

def has_pending_refresh_request(company_id, item):
    return BugReport.query.filter(
        BugReport.company_id == company_id,
        BugReport.report_type == 'expiration',
        BugReport.status == 'pending',
        or_(
            BugReport.item_id == item.id,
            BugReport.title == refresh_request_title(item.title)
        )
    ).first() is not None

def resolve_pending_refresh_requests(item):
    BugReport.query.filter(
        BugReport.report_type == 'expiration',
        BugReport.status == 'pending',
        or_(
            BugReport.item_id == item.id,
            BugReport.title == refresh_request_title(item.title)
        )
    ).update({'status': 'resolved'}, synchronize_session=False)

def get_pending_refresh_item_ids(company_id, items):
    pending = set()
    title_to_id = {item.title: item.id for item in items}
    reports = BugReport.query.filter_by(
        company_id=company_id,
        report_type='expiration',
        status='pending'
    ).all()
    for report in reports:
        if report.item_id:
            pending.add(report.item_id)
        else:
            prefix = 'Solicitação de Renovação: '
            if report.title.startswith(prefix):
                link_title = report.title[len(prefix):]
                if link_title in title_to_id:
                    pending.add(title_to_id[link_title])
    return pending

def create_admin():
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

def passwords_match(password, password_confirm):
    return password == password_confirm

with app.app_context():
    db.create_all()
    migrate_schema()
    create_admin()

# --- ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('company_hub'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- ADMIN PANEL ---

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    companies = Company.query.all()
    return render_template('admin_dashboard.html', companies=companies)

@app.route('/admin/company/add', methods=['POST'])
@login_required
def add_company():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    
    if not passwords_match(password, password_confirm):
        flash('As senhas não conferem. Digite novamente.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    if User.query.filter_by(username=username).first():
        flash('Nome de usuário já existe', 'danger')
    else:
        new_company = Company(name=name)
        db.session.add(new_company)
        db.session.flush()
        
        new_user = User(username=username, role='company', company_id=new_company.id)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Empresa adicionada com sucesso', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/company/<int:id>')
@login_required
def view_company_as_admin(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    company = Company.query.get_or_404(id)
    parent_id = request.args.get('folder', type=int)
    
    path = []
    if parent_id:
        temp = Item.query.get(parent_id)
        while temp:
            path.insert(0, temp)
            temp = temp.parent
            
    items = Item.query.filter_by(company_id=id, parent_id=parent_id).order_by(Item.type.asc(), Item.title.asc()).all()
    return render_template('company_hub.html', company=company, items=items, path=path, current_folder=parent_id, is_admin=True, now=datetime.now(), pending_refresh_ids=set())

@app.route('/admin/company/edit/<int:id>', methods=['POST'])
@login_required
def edit_company(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    company = Company.query.get_or_404(id)
    company.name = request.form.get('name')
    company.fantasy_name = request.form.get('fantasy_name')
    company.contact_email = request.form.get('contact_email')
    company.contact_phone = request.form.get('contact_phone')
    
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    
    user = company.user
    if user:
        user.username = username
        if password:
            if not passwords_match(password, password_confirm):
                flash('As senhas não conferem. Digite novamente.', 'danger')
                return redirect(url_for('admin_dashboard'))
            user.set_password(password)
            
    db.session.commit()
    flash('Empresa atualizada com sucesso', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/company/delete/<int:id>')
@login_required
def delete_company(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    company = Company.query.get_or_404(id)
    db.session.delete(company)
    db.session.commit()
    flash('Empresa removida com sucesso', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/item/add/<int:company_id>', methods=['POST'])
@login_required
def add_item(company_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    title = request.form.get('title')
    item_type = request.form.get('type')
    url = request.form.get('url')
    expires_at_str = request.form.get('expires_at')
    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d') if expires_at_str else None
    link_password = request.form.get('link_password') or None
    parent_id = request.form.get('parent_id') or None
    if parent_id == 'None': parent_id = None
    
    new_item = Item(title=title, type=item_type, url=url, expires_at=expires_at, link_password=link_password, parent_id=parent_id, company_id=company_id)
    db.session.add(new_item)
    db.session.commit()
    
    return redirect(url_for('view_company_as_admin', id=company_id, folder=parent_id))

@app.route('/admin/item/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_item(item_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    item = Item.query.get_or_404(item_id)
    old_url = item.url
    old_expires_at = item.expires_at
    new_url = request.form.get('url')
    expires_at_str = request.form.get('expires_at')
    new_expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d') if expires_at_str else None

    item.title = request.form.get('title')
    item.url = new_url
    item.expires_at = new_expires_at
    item.link_password = request.form.get('link_password') or None

    if old_url != new_url or old_expires_at != new_expires_at:
        resolve_pending_refresh_requests(item)

    db.session.commit()
    
    return redirect(url_for('view_company_as_admin', id=item.company_id, folder=item.parent_id))

@app.route('/admin/item/delete/<int:item_id>')
@login_required
def delete_item(item_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    item = Item.query.get_or_404(item_id)
    company_id = item.company_id
    parent_id = item.parent_id
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('view_company_as_admin', id=company_id, folder=parent_id))

@app.route('/admin/bugs')
@login_required
def view_bugs():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    tab = request.args.get('tab', 'manual')
    manual_bugs = BugReport.query.filter_by(report_type='manual').order_by(BugReport.created_at.desc()).all()
    expiration_bugs = BugReport.query.filter_by(report_type='expiration').order_by(BugReport.created_at.desc()).all()
    return render_template('admin_bugs.html', manual_bugs=manual_bugs, expiration_bugs=expiration_bugs, active_tab=tab)

@app.route('/admin/bug/resolve/<int:id>')
@login_required
def resolve_bug(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    bug = BugReport.query.get_or_404(id)
    bug.status = 'resolved'
    db.session.commit()
    flash('Erro marcado como resolvido', 'success')
    tab = 'expiration' if bug.report_type == 'expiration' else 'manual'
    return redirect(url_for('view_bugs', tab=tab))

@app.route('/admin/bug/delete/<int:id>')
@login_required
def delete_bug(id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    bug = BugReport.query.get_or_404(id)
    tab = 'expiration' if bug.report_type == 'expiration' else 'manual'
    db.session.delete(bug)
    db.session.commit()
    flash('Log removido com sucesso', 'success')
    return redirect(url_for('view_bugs', tab=tab))

# --- COMPANY HUB ---

@app.route('/hub')
@login_required
def company_hub():
    if current_user.role != 'company':
        return redirect(url_for('index'))
    
    company = current_user.company
    parent_id = request.args.get('folder', type=int)
    
    path = []
    if parent_id:
        temp = Item.query.get(parent_id)
        if temp and temp.company_id == company.id:
            # Server-side check for password protection
            if temp.link_password and temp.id not in session.get('unlocked_items', []):
                flash('Esta pasta é protegida por senha.', 'warning')
                return redirect(url_for('company_hub'))
                
            while temp:
                path.insert(0, temp)
                temp = temp.parent
        else:
            parent_id = None
            
    items = Item.query.filter_by(company_id=company.id, parent_id=parent_id).order_by(Item.type.asc(), Item.title.asc()).all()
    pending_refresh_ids = get_pending_refresh_item_ids(company.id, items)
    return render_template('company_hub.html', company=company, items=items, path=path, current_folder=parent_id, is_admin=False, now=datetime.now(), pending_refresh_ids=pending_refresh_ids)

@app.route('/bug/report', methods=['POST'])
@login_required
def report_bug():
    title = request.form.get('title')
    description = request.form.get('description')
    company_id = current_user.company_id
    
    new_bug = BugReport(
        title=title,
        description=description,
        company_id=company_id,
        user_id=current_user.id,
        report_type='manual'
    )
    db.session.add(new_bug)
    db.session.commit()
    flash('Relato de bug enviado com sucesso. Obrigado!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/item/request_refresh/<int:item_id>')
@login_required
def request_refresh(item_id):
    item = Item.query.get_or_404(item_id)
    if current_user.role != 'company' or item.company_id != current_user.company_id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('index'))

    if item.type != 'link':
        flash('Apenas links podem ter renovação solicitada.', 'danger')
        return redirect(url_for('company_hub', folder=item.parent_id) if item.parent_id else url_for('company_hub'))

    if has_pending_refresh_request(current_user.company_id, item):
        flash('Já existe uma solicitação pendente para este link. Aguarde o administrador atualizar o arquivo.', 'warning')
        return redirect(url_for('company_hub', folder=item.parent_id) if item.parent_id else url_for('company_hub'))

    new_report = BugReport(
        title=refresh_request_title(item.title),
        description=f"O link '{item.title}' foi solicitado para renovação pelo cliente. Por favor, atualize o endereço ou a data de validade.",
        company_id=current_user.company_id,
        user_id=current_user.id,
        report_type='expiration',
        item_id=item.id
    )
    db.session.add(new_report)
    db.session.commit()
    flash('Solicitação de renovação enviada ao administrador com sucesso.', 'success')
    return redirect(url_for('company_hub', folder=item.parent_id) if item.parent_id else url_for('company_hub'))

@app.route('/item/verify-password/<int:item_id>', methods=['POST'])
@login_required
def verify_link_password(item_id):
    item = Item.query.get_or_404(item_id)
    password = request.form.get('password')
    
    if item.link_password == password:
        if 'unlocked_items' not in session:
            session['unlocked_items'] = []
        if item.id not in session['unlocked_items']:
            session['unlocked_items'].append(item.id)
            session.modified = True
            
        return {'success': True, 'url': item.url}
    return {'success': False, 'message': 'Senha incorreta'}, 401

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    new_username = request.form.get('username')
    new_password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    current_password = request.form.get('current_password')
    
    if new_username != current_user.username:
        if User.query.filter_by(username=new_username).first():
            flash('Nome de usuário já está em uso', 'danger')
            return redirect(url_for('profile'))
        current_user.username = new_username
    
    if new_password:
        if not passwords_match(new_password, password_confirm):
            flash('As senhas não conferem. Digite novamente.', 'danger')
            return redirect(url_for('profile'))
        if not current_password or not current_user.check_password(current_password):
            flash('Senha atual incorreta.', 'danger')
            return redirect(url_for('profile'))
        current_user.set_password(new_password)
        
    if current_user.role == 'company':
        company = current_user.company
        company.fantasy_name = request.form.get('fantasy_name')
        company.contact_email = request.form.get('contact_email')
        company.contact_phone = request.form.get('contact_phone')
        company.logo_url = request.form.get('logo_url')
        
    db.session.commit()
    flash('Perfil atualizado com sucesso', 'success')
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)

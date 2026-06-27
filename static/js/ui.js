function togglePasswordVisibility(button) {
    const wrapper = button.closest('.password-field');
    if (!wrapper) return;
    const input = wrapper.querySelector('input');
    const icon = button.querySelector('i');
    const isHidden = input.type === 'password';
    input.type = isHidden ? 'text' : 'password';
    icon.classList.toggle('fa-eye', !isHidden);
    icon.classList.toggle('fa-eye-slash', isHidden);
}

const ALERT_STYLES = {
    info: {
        icon: 'fas fa-info-circle',
        iconBg: 'bg-blue-100 text-blue-600 border border-blue-200',
        btnClass: 'w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-blue-500/20'
    },
    warning: {
        icon: 'fas fa-exclamation-triangle',
        iconBg: 'bg-orange-100 text-orange-600 border border-orange-200',
        btnClass: 'w-full bg-orange-500 hover:bg-orange-600 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-orange-500/20'
    },
    error: {
        icon: 'fas fa-circle-exclamation',
        iconBg: 'bg-red-100 text-red-600 border border-red-200',
        btnClass: 'w-full bg-red-600 hover:bg-red-700 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-red-500/20'
    },
    success: {
        icon: 'fas fa-circle-check',
        iconBg: 'bg-emerald-100 text-emerald-600 border border-emerald-200',
        btnClass: 'w-full bg-emerald-600 hover:bg-emerald-700 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-emerald-500/20'
    }
};

function showAlertModal({ title, message, type = 'info', onClose }) {
    const modal = document.getElementById('modalAlert');
    if (!modal) {
        window.alert(message);
        if (onClose) onClose();
        return;
    }

    const style = ALERT_STYLES[type] || ALERT_STYLES.info;
    document.getElementById('alert_title').textContent = title || 'Aviso';
    document.getElementById('alert_message').textContent = message || '';

    const iconWrap = document.getElementById('alert_icon_wrap');
    iconWrap.className = `w-20 h-20 rounded-[2rem] flex items-center justify-center text-3xl mx-auto shadow-2xl ${style.iconBg}`;
    document.getElementById('alert_icon').className = style.icon;

    const btn = document.getElementById('alert_btn');
    btn.className = style.btnClass;

    window._alertOnClose = onClose || null;
    modal.classList.remove('hidden');
    requestAnimationFrame(() => modal.querySelector('.alert-dialog').classList.add('alert-dialog-visible'));
}

function closeAlertModal() {
    const modal = document.getElementById('modalAlert');
    if (!modal) return;
    const dialog = modal.querySelector('.alert-dialog');
    dialog.classList.remove('alert-dialog-visible');
    setTimeout(() => {
        modal.classList.add('hidden');
        if (window._alertOnClose) {
            const cb = window._alertOnClose;
            window._alertOnClose = null;
            cb();
        }
    }, 200);
}

function openConfirmModal({ title, message, confirmUrl, confirmLabel, iconClass, iconBg, btnClass }) {
    const modal = document.getElementById('modalConfirmAction');
    if (!modal) {
        showAlertModal({ title, message, type: 'warning', onClose: () => { window.location.href = confirmUrl; } });
        return;
    }

    document.getElementById('confirm_title').textContent = title;
    document.getElementById('confirm_message').textContent = message;
    document.getElementById('confirm_btn').href = confirmUrl;
    document.getElementById('confirm_btn_label').textContent = confirmLabel || 'Confirmar Exclusão';

    const iconWrap = document.getElementById('confirm_icon_wrap');
    iconWrap.className = `w-20 h-20 rounded-[2rem] flex items-center justify-center text-3xl mx-auto shadow-2xl ${iconBg || 'bg-red-100 text-red-600 border border-red-200'}`;
    document.getElementById('confirm_icon').className = iconClass || 'fas fa-trash-alt';

    const btn = document.getElementById('confirm_btn');
    btn.className = btnClass || 'w-full bg-red-600 hover:bg-red-700 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-red-500/20';

    modal.classList.remove('hidden');
    requestAnimationFrame(() => modal.querySelector('.confirm-dialog').classList.add('confirm-dialog-visible'));
}

function closeConfirmModal() {
    const modal = document.getElementById('modalConfirmAction');
    if (!modal) return;
    const dialog = modal.querySelector('.confirm-dialog');
    dialog.classList.remove('confirm-dialog-visible');
    setTimeout(() => modal.classList.add('hidden'), 200);
}

function confirmDelete(url, title, message) {
    openConfirmModal({
        title: title || 'Confirmar Exclusão',
        message: message || 'Esta ação não pode ser desfeita.',
        confirmUrl: url,
        confirmLabel: 'Sim, Excluir',
        iconClass: 'fas fa-trash-alt',
        iconBg: 'bg-red-100 text-red-600 border border-red-200'
    });
    return false;
}

function confirmRenewal(url, itemTitle) {
    openConfirmModal({
        title: 'Solicitar Renovação',
        message: `Deseja solicitar a renovação do link "${itemTitle}"? O administrador será notificado para atualizar o endereço ou a data de validade.`,
        confirmUrl: url,
        confirmLabel: 'Enviar Solicitação',
        iconClass: 'fas fa-sync-alt',
        iconBg: 'bg-blue-100 text-blue-600 border border-blue-200',
        btnClass: 'w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-black uppercase tracking-widest text-[10px] transition active:scale-95 shadow-lg shadow-blue-500/20'
    });
    return false;
}

function validatePasswordForm(form, options = {}) {
    const password = form.querySelector('[name="password"]');
    const confirm = form.querySelector('[name="password_confirm"]');
    const current = form.querySelector('[name="current_password"]');

    if (!password || !confirm) return true;

    const pwd = password.value;
    const pwdConfirm = confirm.value;

    if (options.requirePassword && !pwd) {
        showAlertModal({
            title: 'Senha Obrigatória',
            message: 'Informe a senha para continuar.',
            type: 'warning',
            onClose: () => password.focus()
        });
        return false;
    }

    if (!pwd && !pwdConfirm) return true;

    if (pwd !== pwdConfirm) {
        showAlertModal({
            title: 'Senhas Diferentes',
            message: 'As senhas não conferem. Digite novamente.',
            type: 'error',
            onClose: () => confirm.focus()
        });
        return false;
    }

    if (options.requireCurrent && current && pwd) {
        if (!current.value) {
            showAlertModal({
                title: 'Senha Atual Necessária',
                message: 'Informe a senha atual para alterar a senha.',
                type: 'warning',
                onClose: () => current.focus()
            });
            return false;
        }
    }

    return true;
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form[data-validate-password]').forEach(form => {
        form.addEventListener('submit', (e) => {
            const requireCurrent = form.dataset.requireCurrent === 'true';
            const requirePassword = form.dataset.requirePassword === 'true';
            if (!validatePasswordForm(form, { requireCurrent, requirePassword })) {
                e.preventDefault();
            }
        });
    });
});

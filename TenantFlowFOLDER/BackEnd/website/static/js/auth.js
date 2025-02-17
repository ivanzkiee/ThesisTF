document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(function() {
        document.querySelectorAll('.alert').forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Real-time form validation
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });

        // Password strength indicator
        const passwordInput = document.querySelector('input[name="password1"]');
        if (passwordInput) {
            passwordInput.addEventListener('input', function() {
                const password = this.value;
                let strength = 0;
                
                if (password.length >= 8) strength++;
                if (/[A-Z]/.test(password)) strength++;
                if (/[0-9]/.test(password)) strength++;
                
                const strengthBar = document.querySelector('.password-strength');
                if (strengthBar) {
                    strengthBar.className = 'password-strength progress-bar';
                    switch(strength) {
                        case 1:
                            strengthBar.classList.add('bg-danger');
                            strengthBar.style.width = '33%';
                            break;
                        case 2:
                            strengthBar.classList.add('bg-warning');
                            strengthBar.style.width = '66%';
                            break;
                        case 3:
                            strengthBar.classList.add('bg-success');
                            strengthBar.style.width = '100%';
                            break;
                        default:
                            strengthBar.style.width = '0%';
                    }
                }
            });
        }
    }
}); 
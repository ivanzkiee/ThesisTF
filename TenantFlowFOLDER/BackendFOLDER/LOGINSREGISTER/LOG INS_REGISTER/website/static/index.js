function deleteNote(noteId) {
    fetch("/delete-note", {
      method: "POST",
      body: JSON.stringify({ noteId: noteId }),
    }).then((_res) => {
      window.location.href = "/";
    });
  }

document.addEventListener('DOMContentLoaded', function() {
    // Get the delete account form
    const deleteAccountForm = document.querySelector('#deleteAccountModal form');
    
    if (deleteAccountForm) {
        deleteAccountForm.addEventListener('submit', function(e) {
            if (!confirm('Are you absolutely sure you want to delete your account? This cannot be undone!')) {
                e.preventDefault();
            }
        });
    }

    // Format currency values
    document.querySelectorAll('.value').forEach(element => {
        if (element.textContent.startsWith('$')) {
            const value = parseFloat(element.textContent.replace('$', ''));
            element.textContent = value.toLocaleString('en-US', {
                style: 'currency',
                currency: 'PHP'
            });
        }
    });
});
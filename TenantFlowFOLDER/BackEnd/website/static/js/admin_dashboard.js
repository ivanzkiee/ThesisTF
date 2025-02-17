// Global calendar variable
let calendar;

// Function declarations
function editUnit(unitId) {
    // Implement unit editing functionality
    console.log('Edit unit:', unitId);
}

function updateMaintenanceStatus(requestId) {
    // Implement maintenance status update
    console.log('Update maintenance:', requestId);
}

function markAsPaid(paymentId) {
    fetch(`/mark-payment-paid/${paymentId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

function saveEvent() {
    const data = {
        title: document.getElementById('eventTitle').value,
        type: document.getElementById('eventType').value,
        description: document.getElementById('eventDescription').value,
        start: document.getElementById('eventDate').value,
        allDay: document.getElementById('allDay').checked
    };

    fetch('/add-calendar-event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            var modal = bootstrap.Modal.getInstance(document.getElementById('eventModal'));
            modal.hide();
            calendar.refetchEvents();
        }
    });
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
    initializeCharts();
    initializeDateTime();
    initializeNotifications();
    initializeActivityTable();
});

function initializeCalendar() {
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: '/calendar-events',
        selectable: true,
        select: function(info) {
            const modal = new bootstrap.Modal(document.getElementById('eventModal'));
            document.getElementById('eventDate').value = info.startStr;
            modal.show();
        },
        eventClick: function(info) {
            if (info.event.extendedProps.type === 'complaint' && 
                info.event.extendedProps.status === 'pending') {
                if (confirm('Mark this complaint as resolved?')) {
                    updateEventStatus(info.event.id, 'resolved');
                }
            }
        }
    });
    calendar.render();
}

function initializeCharts() {
    // Payment Chart
    new Chart(
        document.getElementById('paymentTrendChart').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: window.chartConfig.payment.labels,
                datasets: [{
                    label: 'Payment Trends',
                    data: window.chartConfig.payment.data,
                    borderColor: '#4CAF50',
                    tension: 0.1
                }]
            }
        }
    );

    // Occupancy Chart
    new Chart(
        document.getElementById('occupancyChart').getContext('2d'),
        {
            type: 'line',
            data: {
                labels: window.chartConfig.occupancy.labels,
                datasets: [{
                    label: 'Occupancy Rate',
                    data: window.chartConfig.occupancy.data,
                    borderColor: '#2196F3',
                    tension: 0.1
                }]
            }
        }
    );
}

function initializeDateTime() {
    function updateDateTime() {
        const now = new Date();
        document.getElementById('currentTime').textContent = now.toLocaleTimeString();
        document.getElementById('currentDate').textContent = now.toLocaleDateString();
    }
    setInterval(updateDateTime, 1000);
    updateDateTime();
}

function initializeNotifications() {
    const toast = new bootstrap.Toast(document.getElementById('notificationToast'));
    
    function checkNotifications() {
        fetch('/admin/check-notifications')
            .then(response => response.json())
            .then(data => {
                if (data.notifications.length > 0) {
                    updateNotificationBadge(data.notifications.length);
                    showNotification(data.notifications[0]);
                }
            });
    }

    function showNotification(notification) {
        document.getElementById('toastTime').textContent = new Date().toLocaleTimeString();
        document.getElementById('toastMessage').textContent = notification.message;
        toast.show();
    }

    function updateNotificationBadge(count) {
        const badge = document.getElementById('notificationBadge');
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }

    setInterval(checkNotifications, 30000);
    checkNotifications();
}

function initializeActivityTable() {
    document.getElementById('refreshActivity').addEventListener('click', function() {
        fetch('/admin/recent-activities')
            .then(response => response.json())
            .then(data => {
                updateActivityTable(data.activities);
            });
    });

    document.querySelectorAll('.view-details').forEach(button => {
        button.addEventListener('click', function() {
            const activityId = this.dataset.id;
            fetch(`/admin/activity/${activityId}`)
                .then(response => response.json())
                .then(data => {
                    showActivityDetails(data);
                });
        });
    });
}

function updateActivityTable(activities) {
    const tbody = document.querySelector('#activityTable tbody');
    tbody.innerHTML = activities.map(activity => `
        <tr>
            <td>${new Date(activity.timestamp).toLocaleString()}</td>
            <td>
                <span class="badge bg-${activity.type_color}">
                    ${activity.type}
                </span>
            </td>
            <td>${activity.description}</td>
            <td>
                <span class="badge bg-${activity.status_color}">
                    ${activity.status}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-primary view-details" 
                        data-id="${activity.id}"
                        data-bs-toggle="modal" 
                        data-bs-target="#activityModal">
                    View
                </button>
            </td>
        </tr>
    `).join('');
}

function showActivityDetails(activity) {
    const modalBody = document.querySelector('#activityModal .modal-body');
    modalBody.innerHTML = `
        <div class="mb-3">
            <strong>Type:</strong> ${activity.type}
        </div>
        <div class="mb-3">
            <strong>Description:</strong> ${activity.description}
        </div>
        <div class="mb-3">
            <strong>Status:</strong> ${activity.status}
        </div>
        <div class="mb-3">
            <strong>Time:</strong> ${new Date(activity.timestamp).toLocaleString()}
        </div>
        ${activity.additional_info ? `
        <div class="mb-3">
            <strong>Additional Info:</strong>
            <pre class="mt-2">${JSON.stringify(activity.additional_info, null, 2)}</pre>
        </div>
        ` : ''}
    `;
}

// CRUD Functions
function editNote(id) {
    fetch(`/admin/note/${id}`)
        .then(response => response.json())
        .then(data => {
            console.log('Editing note:', id);
        });
}

function deleteNote(id) {
    if (confirm('Are you sure you want to delete this note?')) {
        fetch(`/admin/note/${id}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) location.reload();
            });
    }
}

function viewPayment(id) {
    window.location.href = `/admin/payment/${id}`;
}

function saveNote() {
    const form = document.getElementById('noteForm');
    const formData = new FormData(form);
    
    fetch('/admin/note', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) location.reload();
    });
}

function showWarningModal(tenantId) {
    document.getElementById('warningTenantId').value = tenantId;
    new bootstrap.Modal(document.getElementById('warningModal')).show();
}

function sendWarning() {
    const tenantId = document.getElementById('warningTenantId').value;
    const message = document.getElementById('warningMessage').value;
    
    fetch(`/admin/send-warning/${tenantId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

function showApproveModal(paymentId) {
    document.getElementById('approvePaymentId').value = paymentId;
    new bootstrap.Modal(document.getElementById('approvePaymentModal')).show();
}

function approvePayment() {
    const paymentId = document.getElementById('approvePaymentId').value;
    const notes = document.getElementById('adminNotes').value;
    
    fetch(`/admin/approve-payment/${paymentId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ notes: notes })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
} 
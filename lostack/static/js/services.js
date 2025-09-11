// Enhanced service management functionality
document.addEventListener('DOMContentLoaded', function () {
  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });
});

// Function to launch service actions with terminal modal
function serviceActionWithTerminal(streamUrl, actionTitle) {
  // Update the terminal modal title
  const modalTitle = document.getElementById('terminalModalLabel');
  if (modalTitle) {
    modalTitle.innerHTML = `<i class="bi bi-terminal me-2"></i>${actionTitle}`;
  }
  
  // Launch the terminal modal with the stream
  launchTerminalModal(streamUrl);
}

// Variables to store delete action details
let deleteServiceUrl = null;
let deleteServiceName = null;

// Function to show delete confirmation modal
function showDeleteConfirmation(serviceId, serviceName, deleteUrl) {
  deleteServiceUrl = deleteUrl;
  deleteServiceName = serviceName;
  
  // Update modal title with service name
  const modalLabel = document.getElementById('deleteServiceModalLabel');
  modalLabel.innerHTML = `<i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Delete "${serviceName}"`;
  
  // Show the modal
  const deleteModal = new bootstrap.Modal(document.getElementById('deleteServiceModal'));
  deleteModal.show();
}

// Handle delete confirmation
document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
  if (deleteServiceUrl) {
    // Close the modal
    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteServiceModal'));
    deleteModal.hide();
    
    // Execute the delete action with terminal
    serviceActionWithTerminal(deleteServiceUrl, `${deleteServiceName} - Delete Service`);
    
    // Reset variables
    deleteServiceUrl = null;
    deleteServiceName = null;
  }
});

// Add visual feedback when hovering over action buttons
document.addEventListener('DOMContentLoaded', function() {
  const actionButtons = document.querySelectorAll('.btn-action');
  
  actionButtons.forEach(button => {
    button.addEventListener('mouseenter', function() {
      this.classList.add('shadow-sm');
    });
    
    button.addEventListener('mouseleave', function() {
      this.classList.remove('shadow-sm');
    });
  });
});
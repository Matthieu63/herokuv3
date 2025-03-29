document.addEventListener('DOMContentLoaded', function() {
    function attachProgress(formId, containerId, barId, useAjax) {
      const form = document.getElementById(formId);
      if (!form) return;
  
      const container = document.getElementById(containerId);
      const bar = document.getElementById(barId);
  
      form.addEventListener('submit', function(e) {
        // Show & reset
        container.style.display = 'block';
        bar.style.width = '0%';
        bar.textContent = '0%';
  
        let progress = 0;
        const interval = setInterval(() => {
          progress = Math.min(progress + Math.floor(Math.random() * 10) + 5, 90);
          bar.style.width = progress + '%';
          bar.textContent = progress + '%';
        }, 300);
  
        if (useAjax) {
          e.preventDefault();
          const formData = new FormData(form);
          fetch(form.action, { method: 'POST', body: formData })
            .then(resp => {
              clearInterval(interval);
              bar.style.width = '100%';
              bar.textContent = '100%';
              return resp.ok ? resp.json().catch(() => {}) : Promise.reject(resp.statusText);
            })
            .then(data => window.location.href = '/espagnol/')
            .catch(err => {
              clearInterval(interval);
              alert("Erreur lors de l'ajout du mot");
              console.error(err);
            });
        } else {
          // Normal submit → clear interval on navigation
          window.addEventListener('beforeunload', () => clearInterval(interval));
        }
      });
    }
  
    attachProgress('add-word-form', 'progress-bar-container', 'progress-bar', true);
    attachProgress('bulk-add-form', 'bulk-progress-bar-container', 'bulk-progress-bar', false);
  });
  
document.addEventListener('DOMContentLoaded', function() {
  // Initialisation de l'éditeur Quill pour la synthèse uniquement
  const quillSynthese = new Quill('#synthese-editor', {
    theme: 'snow',
    modules: {
      toolbar: [
        [{ 'color': [] }, { 'background': [] }],
        ['bold', 'italic', 'underline'],
        [{ header: [1, 2, 3, false] }],
        [{ list: 'ordered' }, { list: 'bullet' }],
        ['link', 'image']
      ]
    }
  });
  
  // Initialisation de l'éditeur de la modale
  const quillModal = new Quill('#modal-editor', {
    theme: 'snow',
    modules: {
      toolbar: [
        [{ 'color': [] }, { 'background': [] }],
        ['bold', 'italic', 'underline'],
        [{ header: [1, 2, 3, false] }],
        [{ list: 'ordered' }, { list: 'bullet' }],
        ['link', 'image']
      ]
    }
  });
  
  let currentWordId = null;
  let currentField = null;
  let currentCell = null;
  
  // Gestion du formulaire d'ajout
  const addWordForm = document.getElementById('add-word-form');
  if (addWordForm) {
    addWordForm.addEventListener('submit', function(e) {
      e.preventDefault();
      const submitButton = addWordForm.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      
      const word = document.getElementById('word').value.trim();
      // Récupération du contenu de l'éditeur Quill pour la synthèse
      const synthese = quillSynthese.root.innerHTML;
      console.log("DEBUG: Synthèse récupérée depuis Quill :", synthese);
      
      const youglish = document.getElementById('youglish').value.trim();
      const tagsSelect = document.getElementById('tags');
      const selectedTags = Array.from(tagsSelect.selectedOptions).map(option => option.value);
      const tags = selectedTags.join(', ');
      
      // Récupération de la case à cocher pour désactiver la génération automatique
      const disableAutoSynthese = document.getElementById('disable-auto-synthese').checked;
      
      const imageInput = document.getElementById('image');
      const file = imageInput.files[0];
      
      const sendData = (imageData) => {
        const dataToSend = { 
          word, 
          synthese, 
          youglish, 
          tags, 
          image: imageData, 
          disable_auto_synthese: disableAutoSynthese 
        };
        console.log("DEBUG: Données envoyées au serveur :", dataToSend);
        fetch('/add', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(dataToSend)
        })
        .then(response => response.json())
        .then(data => {
          if (data.status === 'success') {
            location.reload();
          } else {
            console.error('Erreur lors de l’ajout:', data.message);
            submitButton.disabled = false;
          }
        })
        .catch(error => {
          console.error('Erreur:', error);
          submitButton.disabled = false;
        });
      };

      if (file) {
        const reader = new FileReader();
        reader.onload = function(event) {
          sendData(event.target.result);
        };
        reader.readAsDataURL(file);
      } else {
        sendData("");
      }
    });
  }
  
  // Gestion de l'édition via la modale pour les cellules éditables
  document.querySelectorAll('td.editable').forEach(cell => {
    cell.addEventListener('click', function(e) {
      currentWordId = cell.closest('tr').getAttribute('data-id');
      currentField = cell.getAttribute('data-field');
      currentCell = cell;
      
      if (currentField === 'image') {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = function() {
          const file = fileInput.files[0];
          if (file) {
            const reader = new FileReader();
            reader.onload = function(event) {
              const newImageData = event.target.result;
              fetch('/espagnol/update_word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: currentWordId, field: 'image', value: newImageData })
              })
              .then(response => response.json())
              .then(data => {
                if (data.status === 'success') {
                  currentCell.innerHTML = `<img src="${newImageData}" alt="Image" style="max-width:50px; max-height:50px; cursor:pointer;">`;
                } else {
                  console.error('Erreur lors de la mise à jour de l’image');
                }
              })
              .catch(error => console.error('Erreur:', error));
            };
            reader.readAsDataURL(file);
          }
        };
        fileInput.click();
        return;
      }
      
      if (currentField === 'tags') {
        document.getElementById('modal-editor').style.display = 'none';
        document.getElementById('modal-tags').style.display = 'block';
        const currentTags = cell.innerHTML.replace(/<[^>]*>/g, '').split(',').map(t => t.trim());
        const select = document.getElementById('modal-tags-select');
        Array.from(select.options).forEach(option => {
          option.selected = currentTags.includes(option.value);
        });
      } else {
        document.getElementById('modal-tags').style.display = 'none';
        document.getElementById('modal-editor').style.display = 'block';
        quillModal.clipboard.dangerouslyPasteHTML(cell.innerHTML);
      }
      document.getElementById('editModal').style.display = 'block';
    });
  });
  
  // Fermeture de la modale
  const closeModal = document.querySelector('.modal .close');
  if (closeModal) {
    closeModal.addEventListener('click', function() {
      document.getElementById('editModal').style.display = 'none';
    });
  }
  
  // Sauvegarde des modifications depuis la modale
  document.getElementById('save-button').addEventListener('click', function() {
    let formattedContent;
    if (currentField === 'tags') {
      const select = document.getElementById('modal-tags-select');
      const selectedTags = Array.from(select.selectedOptions).map(option => option.value);
      formattedContent = selectedTags.join(', ');
    } else {
      formattedContent = quillModal.root.innerHTML;
    }
    fetch('/espagnol/update_word', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: currentWordId, field: currentField, value: formattedContent })
    })
    .then(response => response.json())
    .then(data => {
      if (data.status === 'success') {
        currentCell.innerHTML = formattedContent;
        document.getElementById('editModal').style.display = 'none';
      } else {
        console.error('Erreur lors de la mise à jour');
      }
    })
    .catch(error => console.error('Erreur:', error));
  });
  
  // Gestion de la suppression d'un mot
  document.querySelectorAll('.delete-btn').forEach(button => {
    button.addEventListener('click', function() {
      const wordId = button.getAttribute('data-id');
      if (confirm("Êtes-vous sûr de vouloir supprimer ce mot ?")) {
        fetch('/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: wordId })
        })
        .then(response => response.json())
        .then(data => {
          if (data.status === 'success') {
            location.reload();
          } else {
            console.error("Erreur lors de la suppression:", data.message);
          }
        })
        .catch(error => console.error("Erreur:", error));
      }
    });
  });
  
  // Gestion de la notation par étoiles
  document.querySelectorAll('.star-rating').forEach(ratingDiv => {
    ratingDiv.querySelectorAll('.star').forEach(starElem => {
      starElem.addEventListener('click', function() {
        const ratingValue = parseInt(starElem.getAttribute('data-value'));
        const wordId = ratingDiv.getAttribute('data-id');
        ratingDiv.querySelectorAll('.star').forEach(s => {
          if (parseInt(s.getAttribute('data-value')) <= ratingValue) {
            s.classList.add('selected');
          } else {
            s.classList.remove('selected');
          }
        });
        fetch('/update_note', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: wordId, note: ratingValue })
        })
        .then(response => response.json())
        .then(data => {
          if (data.status !== 'success') {
            console.error('Erreur lors de l’enregistrement de la note');
          }
        })
        .catch(error => console.error('Erreur:', error));
      });
    });
  });
});

// Ajoutez ce code à votre fichier script.js

// Modal pour les doublons
let duplicateModal;
let currentDuplicateWord = "";

document.addEventListener('DOMContentLoaded', function() {
  // Créer une modal pour les doublons
  setupDuplicateModal();
  
  // Ajouter la détection de doublons au formulaire d'ajout
  setupDuplicateDetection();
  
  // Ajouter la détection de doublons à l'ajout en masse
  setupBulkDuplicateDetection();
});

function setupDuplicateModal() {
  // Créer l'élément modal s'il n'existe pas déjà
  if (!document.getElementById('duplicateModal')) {
    const modalHTML = `
      <div id="duplicateModal" class="modal">
        <div class="modal-content">
          <span class="close" id="closeDuplicateModal">&times;</span>
          <h2>Mot déjà existant</h2>
          <p>Le mot <strong id="duplicateWordName"></strong> existe déjà dans la base de données.</p>
          <div id="duplicateWordDetails">
            <p><strong>Synthèse:</strong> <span id="duplicateWordSynthese"></span></p>
            <p><strong>Tags:</strong> <span id="duplicateWordTags"></span></p>
            <div id="duplicateWordImageContainer"></div>
          </div>
          <p>Que souhaitez-vous faire ?</p>
          <div style="display: flex; justify-content: space-between; margin-top: 20px;">
            <button id="skipDuplicateBtn" class="btn btn-secondary">Ignorer ce mot</button>
            <button id="addAnywayBtn" class="btn btn-primary">Ajouter quand même</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Ajouter le style pour le bouton
    const style = document.createElement('style');
    style.textContent = `
      .btn {
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
      }
      .btn-primary {
        background-color: #007BFF;
        color: white;
      }
      .btn-secondary {
        background-color: #6c757d;
        color: white;
      }
      .btn:hover {
        opacity: 0.9;
      }
    `;
    document.head.appendChild(style);
    
    // Récupérer la référence à la modal
    duplicateModal = document.getElementById('duplicateModal');
    
    // Fermer la modal en cliquant sur X
    document.getElementById('closeDuplicateModal').addEventListener('click', function() {
      duplicateModal.style.display = 'none';
    });
    
    // Fermer la modal en cliquant en dehors
    window.addEventListener('click', function(event) {
      if (event.target === duplicateModal) {
        duplicateModal.style.display = 'none';
      }
    });
  } else {
    duplicateModal = document.getElementById('duplicateModal');
  }
}

function showDuplicateModal(wordData, onSkip, onAddAnyway) {
  // Remplir les détails du mot dans la modal
  document.getElementById('duplicateWordName').textContent = wordData.word;
  
  // Gérer le HTML dans la synthèse
  const syntheseElem = document.getElementById('duplicateWordSynthese');
  syntheseElem.innerHTML = wordData.synthese || 'Aucune synthèse disponible';
  
  document.getElementById('duplicateWordTags').textContent = wordData.tags || 'Aucun tag';
  
  // Afficher l'image si elle existe
  const imageContainer = document.getElementById('duplicateWordImageContainer');
  imageContainer.innerHTML = '';
  
  if (wordData.image) {
    const img = document.createElement('img');
    img.src = wordData.image;
    img.alt = `Image de ${wordData.word}`;
    img.style.maxWidth = '200px';
    img.style.maxHeight = '200px';
    img.style.display = 'block';
    img.style.margin = '10px auto';
    imageContainer.appendChild(img);
  } else {
    imageContainer.innerHTML = '<p>Aucune image disponible</p>';
  }
  
  // Configurer les boutons
  const skipBtn = document.getElementById('skipDuplicateBtn');
  const addAnywayBtn = document.getElementById('addAnywayBtn');
  
  // Supprimer les anciens écouteurs d'événements
  skipBtn.replaceWith(skipBtn.cloneNode(true));
  addAnywayBtn.replaceWith(addAnywayBtn.cloneNode(true));
  
  // Ajouter les nouveaux écouteurs d'événements
  document.getElementById('skipDuplicateBtn').addEventListener('click', function() {
    duplicateModal.style.display = 'none';
    if (typeof onSkip === 'function') onSkip();
  });
  
  document.getElementById('addAnywayBtn').addEventListener('click', function() {
    duplicateModal.style.display = 'none';
    if (typeof onAddAnyway === 'function') onAddAnyway();
  });
  
  // Afficher la modal
  duplicateModal.style.display = 'block';
}

function checkIfWordExists(word) {
  return fetch('/check_duplicate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ word: word })
  })
  .then(response => response.json())
  .then(data => {
    return data;
  })
  .catch(error => {
    console.error('Error checking for duplicate word:', error);
    return { status: 'error', message: 'Erreur lors de la vérification du mot' };
  });
}

function setupDuplicateDetection() {
  const addWordForm = document.getElementById('add-word-form');
  if (!addWordForm) return;
  
  addWordForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const wordInput = document.getElementById('word');
    const word = wordInput.value.trim();
    
    if (!word) {
      alert('Veuillez entrer un mot');
      return;
    }
    
    checkIfWordExists(word).then(result => {
      if (result.status === 'duplicate') {
        showDuplicateModal(result.word, 
          // onSkip
          function() {
            // Réinitialiser le formulaire
            wordInput.value = '';
            document.getElementById('synthese-editor').querySelector('.ql-editor').innerHTML = '';
            document.getElementById('youglish').value = '';
            // Réinitialiser les tags
            const tagsSelect = document.getElementById('tags');
            if (tagsSelect) {
              Array.from(tagsSelect.options).forEach(option => {
                option.selected = false;
              });
            }
          },
          // onAddAnyway
          function() {
            // Soumettre le formulaire avec le contenu actuel
            submitAddWordForm();
          }
        );
      } else {
        // Aucun doublon, soumettre le formulaire
        submitAddWordForm();
      }
    });
  });
}

function submitAddWordForm() {
  const wordInput = document.getElementById('word');
  const syntheseEditor = document.getElementById('synthese-editor').querySelector('.ql-editor');
  const youglishInput = document.getElementById('youglish');
  const tagsSelect = document.getElementById('tags');
  const disableAutoSyntheseCheckbox = document.getElementById('disable-auto-synthese');
  const imageInput = document.getElementById('image');
  
  // Récupérer les valeurs
  const word = wordInput.value.trim();
  const synthese = syntheseEditor.innerHTML;
  const youglish = youglishInput.value.trim();
  const selectedTags = Array.from(tagsSelect.selectedOptions).map(option => option.value);
  const disableAutoSynthese = disableAutoSyntheseCheckbox.checked;
  
  // Préparation des données du formulaire
  const formData = {
    word: word,
    synthese: synthese,
    youglish: youglish,
    tags: selectedTags.join(', '),
    disable_auto_synthese: disableAutoSynthese,
    image: ''  // L'image sera traitée séparément si nécessaire
  };
  
  // Envoyer les données
  fetch('/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(formData)
  })
  .then(response => response.json())
  .then(data => {
    if (data.status === 'success') {
      // Réinitialiser le formulaire
      wordInput.value = '';
      syntheseEditor.innerHTML = '';
      youglishInput.value = '';
      Array.from(tagsSelect.options).forEach(option => {
        option.selected = false;
      });
      disableAutoSyntheseCheckbox.checked = false;
      
      // Rafraîchir la page pour afficher le nouveau mot
      window.location.reload();
    } else {
      alert('Erreur lors de l\'ajout du mot: ' + (data.message || 'Erreur inconnue'));
    }
  })
  .catch(error => {
    console.error('Error:', error);
    alert('Erreur lors de l\'ajout du mot');
  });
}

function setupBulkDuplicateDetection() {
  // Cette fonction sera implémentée plus tard pour l'ajout en masse
  const bulkAddForm = document.getElementById('bulk-add-form');
  if (!bulkAddForm) return;
  
  // Le code pour la détection de doublons en masse sera ajouté ici
}

// Système de détection de doublons pour les mots

document.addEventListener('DOMContentLoaded', function() {
  // Initialisation des fonctionnalités existantes (à conserver)
  initializeExistingFunctionality();
  
  // Mise en place de la détection de doublons dans le formulaire d'ajout 
  setupDuplicateDetection();
  
  // Mise en place de la modal pour les doublons
  setupDuplicateModal();
});

function initializeExistingFunctionality() {
  // Récupérer les fonctionnalités existantes du script original
  // ...
}

function setupDuplicateModal() {
  // Créer la modal pour les doublons si elle n'existe pas déjà
  if (!document.getElementById('duplicateModal')) {
      const modalHTML = `
          <div id="duplicateModal" class="modal">
              <div class="modal-content">
                  <span class="close" id="closeDuplicateModal">&times;</span>
                  <h2>Mot déjà existant</h2>
                  <p>Le mot <strong id="duplicateWordName"></strong> existe déjà dans la base de données.</p>
                  <div id="duplicateWordDetails">
                      <p><strong>Synthèse:</strong> <span id="duplicateWordSynthese"></span></p>
                      <p><strong>Tags:</strong> <span id="duplicateWordTags"></span></p>
                      <div id="duplicateWordImageContainer"></div>
                  </div>
                  <p>Que souhaitez-vous faire ?</p>
                  <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                      <button id="skipDuplicateBtn" class="btn btn-secondary">Ignorer ce mot</button>
                      <button id="addAnywayBtn" class="btn btn-primary">Ajouter quand même</button>
                  </div>
              </div>
          </div>
      `;
      
      document.body.insertAdjacentHTML('beforeend', modalHTML);
      
      // Ajouter le style pour les boutons
      const style = document.createElement('style');
      style.textContent = `
          .btn {
              padding: 8px 16px;
              border: none;
              border-radius: 4px;
              cursor: pointer;
              font-size: 14px;
          }
          .btn-primary {
              background-color: #007BFF;
              color: white;
          }
          .btn-secondary {
              background-color: #6c757d;
              color: white;
          }
          .btn:hover {
              opacity: 0.9;
          }
      `;
      document.head.appendChild(style);
  }
  
  // Récupérer les références à la modal et ses éléments
  const duplicateModal = document.getElementById('duplicateModal');
  const closeBtn = document.getElementById('closeDuplicateModal');
  
  // Fermer la modal quand on clique sur le X
  if (closeBtn) {
      closeBtn.addEventListener('click', function() {
          duplicateModal.style.display = 'none';
      });
  }
  
  // Fermer la modal quand on clique en dehors
  window.addEventListener('click', function(event) {
      if (event.target === duplicateModal) {
          duplicateModal.style.display = 'none';
      }
  });
}

function showDuplicateModal(wordData, onSkip, onAddAnyway) {
  const duplicateModal = document.getElementById('duplicateModal');
  if (!duplicateModal) return;
  
  // Remplir les détails du mot dans la modal
  document.getElementById('duplicateWordName').textContent = wordData.word;
  
  // Gérer le HTML dans la synthèse
  const syntheseElem = document.getElementById('duplicateWordSynthese');
  syntheseElem.innerHTML = wordData.synthese || 'Aucune synthèse disponible';
  
  document.getElementById('duplicateWordTags').textContent = wordData.tags || 'Aucun tag';
  
  // Afficher l'image si elle existe
  const imageContainer = document.getElementById('duplicateWordImageContainer');
  imageContainer.innerHTML = '';
  
  if (wordData.image) {
      const img = document.createElement('img');
      img.src = wordData.image;
      img.alt = `Image de ${wordData.word}`;
      img.style.maxWidth = '200px';
      img.style.maxHeight = '200px';
      img.style.display = 'block';
      img.style.margin = '10px auto';
      imageContainer.appendChild(img);
  } else {
      imageContainer.innerHTML = '<p>Aucune image disponible</p>';
  }
  
  // Configurer les boutons
  const skipBtn = document.getElementById('skipDuplicateBtn');
  const addAnywayBtn = document.getElementById('addAnywayBtn');
  
  // Supprimer les anciens écouteurs d'événements
  skipBtn.replaceWith(skipBtn.cloneNode(true));
  addAnywayBtn.replaceWith(addAnywayBtn.cloneNode(true));
  
  // Ajouter les nouveaux écouteurs d'événements
  document.getElementById('skipDuplicateBtn').addEventListener('click', function() {
      duplicateModal.style.display = 'none';
      if (typeof onSkip === 'function') onSkip();
  });
  
  document.getElementById('addAnywayBtn').addEventListener('click', function() {
      duplicateModal.style.display = 'none';
      if (typeof onAddAnyway === 'function') onAddAnyway();
  });
  
  // Afficher la modal
  duplicateModal.style.display = 'block';
}

function checkIfWordExists(word) {
  return fetch('/check_duplicate', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify({ word: word })
  })
  .then(response => response.json())
  .catch(error => {
      console.error('Error checking for duplicate word:', error);
      return { status: 'error', message: 'Erreur lors de la vérification du mot' };
  });
}

function setupDuplicateDetection() {
  // Pour le formulaire d'ajout individuel
  const addWordForm = document.getElementById('add-word-form');
  if (addWordForm) {
      addWordForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          const wordInput = document.getElementById('word');
          const word = wordInput.value.trim();
          
          if (!word) {
              alert('Veuillez entrer un mot');
              return;
          }
          
          checkIfWordExists(word).then(result => {
              if (result.status === 'duplicate') {
                  showDuplicateModal(result.word, 
                      // onSkip
                      function() {
                          // Réinitialiser le formulaire
                          wordInput.value = '';
                          if (document.querySelector('.ql-editor')) {
                              document.querySelector('.ql-editor').innerHTML = '';
                          }
                          document.getElementById('youglish').value = '';
                          // Réinitialiser les tags
                          const tagsSelect = document.getElementById('tags');
                          if (tagsSelect) {
                              Array.from(tagsSelect.options).forEach(option => {
                                  option.selected = false;
                              });
                          }
                      },
                      // onAddAnyway
                      function() {
                          // Soumettre le formulaire avec le contenu actuel et force_add=true
                          submitAddWordForm(true);
                      }
                  );
              } else {
                  // Pas de doublon, soumettre normalement
                  submitAddWordForm(false);
              }
          });
      });
  }
}

function submitAddWordForm(forceAdd) {
  // Récupérer les valeurs du formulaire
  const wordInput = document.getElementById('word');
  const word = wordInput.value.trim();
  let synthese = '';
  
  // Récupérer la synthèse de Quill si disponible
  if (document.querySelector('.ql-editor')) {
      synthese = document.querySelector('.ql-editor').innerHTML;
  }
  
  const youglish = document.getElementById('youglish').value.trim();
  const tagsSelect = document.getElementById('tags');
  const selectedTags = Array.from(tagsSelect.selectedOptions).map(option => option.value);
  const disableAutoSynthese = document.getElementById('disable-auto-synthese') && document.getElementById('disable-auto-synthese').checked;
  
  // Préparer les données pour l'envoi
  const formData = {
      word: word,
      synthese: synthese,
      youglish: youglish,
      tags: selectedTags.join(', '),
      disable_auto_synthese: disableAutoSynthese,
      force_add: forceAdd,
      image: ''  // Géré séparément si nécessaire
  };
  
  // Envoyer la requête AJAX
  fetch('/add', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData)
  })
  .then(response => response.json())
  .then(data => {
      if (data.status === 'success') {
          // Succès, recharger la page
          window.location.reload();
      } else if (data.status === 'duplicate' && !forceAdd) {
          // Si doublon détecté mais pas forceAdd, afficher le message
          alert(data.message || 'Ce mot existe déjà dans la base de données.');
      } else {
          // Erreur
          alert(data.message || 'Erreur lors de l\'ajout du mot');
      }
  })
  .catch(error => {
      console.error('Error:', error);
      alert('Erreur lors de l\'ajout du mot');
  });
}

// Fonctions existantes à conserver
// ...
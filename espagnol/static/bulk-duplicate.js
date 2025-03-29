// Ajoutez ce code à votre fichier script.js ou dans un nouveau fichier bulk-duplicate.js

document.addEventListener('DOMContentLoaded', function() {
  // Configuration pour l'ajout en masse
  setupBulkDuplicateDetection();
});

function setupBulkDuplicateDetection() {
  const bulkAddForm = document.getElementById('bulk-add-form');
  if (!bulkAddForm) return;
  
  const wordsTextarea = document.getElementById('words_text');
  const checkDuplicatesBtn = document.getElementById('check-duplicates-btn');
  const duplicatesResult = document.getElementById('duplicates-result');
  const newWordsList = document.getElementById('new-words-list');
  const duplicateWordsList = document.getElementById('duplicate-words-list');
  const newWordsCount = document.getElementById('new-words-count');
  const duplicateWordsCount = document.getElementById('duplicate-words-count');
  const addNewWordsBtn = document.getElementById('add-new-words-btn');
  const addAllWordsBtn = document.getElementById('add-all-words-btn');
  
  let newWords = [];
  let duplicateWords = [];
  
  // Empêcher la soumission directe du formulaire
  bulkAddForm.addEventListener('submit', function(e) {
    // Ne pas bloquer si l'action est explicitement demandée par les boutons
    if (!e.submitter || !e.submitter.id) {
      e.preventDefault();
      checkDuplicatesBtn.click();
    }
  });
  
  // Vérification des doublons
  checkDuplicatesBtn.addEventListener('click', function() {
    const wordsText = wordsTextarea.value.trim();
    if (!wordsText) {
      alert('Veuillez entrer au moins un mot');
      return;
    }
    
    const wordsList = wordsText.split('\n')
      .map(w => w.trim())
      .filter(w => w);
      
    if (wordsList.length === 0) {
      alert('Aucun mot valide trouvé');
      return;
    }
    
    // Indiquer que la vérification est en cours
    checkDuplicatesBtn.textContent = 'Vérification en cours...';
    checkDuplicatesBtn.disabled = true;
    
    // Vérifier les doublons en masse
    fetch('/check_duplicates_bulk', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ words: wordsList })
    })
    .then(response => response.json())
    .then(result => {
      // Réinitialiser les listes
      newWords = result.new_words || [];
      duplicateWords = result.duplicates || [];
      
      // Remplir la liste des nouveaux mots
      newWordsList.innerHTML = '';
      newWords.forEach(word => {
        const li = document.createElement('li');
        li.textContent = word;
        li.style.color = '#28a745';
        newWordsList.appendChild(li);
      });
      
      // Remplir la liste des doublons
      duplicateWordsList.innerHTML = '';
      duplicateWords.forEach(item => {
        const li = document.createElement('li');
        
        // Créer un lien pour ouvrir la modal de détails
        const wordLink = document.createElement('a');
        wordLink.textContent = item.word;
        wordLink.href = 'javascript:void(0);';
        wordLink.style.color = '#dc3545';
        wordLink.style.textDecoration = 'underline';
        wordLink.style.cursor = 'pointer';
        
        wordLink.addEventListener('click', function() {
          showDuplicateModal(item.existing);
        });
        
        li.appendChild(wordLink);
        duplicateWordsList.appendChild(li);
      });
      
      // Mettre à jour les compteurs
      newWordsCount.textContent = newWords.length;
      duplicateWordsCount.textContent = duplicateWords.length;
      
      // Afficher le résultat
      duplicatesResult.style.display = 'block';
      
      // Réinitialiser le bouton
      checkDuplicatesBtn.textContent = 'Vérifier les doublons';
      checkDuplicatesBtn.disabled = false;
    })
    .catch(error
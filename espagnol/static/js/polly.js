/**
 * Script pour l'intégration d'Amazon Polly dans toutes les pages
 */

// Variables globales pour la gestion audio
let currentAudio = null;
let currentPollyVoice = 'Lucia'; // Voix par défaut espagnole

// Chargement de la voix préférée lors de l'initialisation
document.addEventListener('DOMContentLoaded', async function() {
  try {
    const response = await fetch('/espagnol/api/voice-settings/default');
    if (response.ok) {
      const data = await response.json();
      currentPollyVoice = data.voice || 'Lucia';
      console.log('Voix par défaut chargée:', currentPollyVoice);
      
      // Mise à jour du sélecteur de voix s'il existe
      const voiceSelector = document.getElementById('voice-selector');
      if (voiceSelector) {
        voiceSelector.value = currentPollyVoice;
      }
    }
  } catch (error) {
    console.error('Erreur lors du chargement de la voix par défaut:', error);
  }
});

/**
 * Fonction pour lire un texte via Amazon Polly
 * @param {string} text - Le texte à lire
 * @param {string} language - Code de langue (es-ES, fr-FR, etc.)
 * @param {Object} options - Options supplémentaires (élément à mettre en surbrillance, callback, etc.)
 */
async function playPollyAudio(text, language = 'es-ES', options = {}) {
  // Arrêter l'audio en cours s'il y en a un
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  
  if (!text) return;
  
  try {
    // Mettre à jour l'interface utilisateur si un bouton est fourni
    const button = options.button || null;
    const originalButtonContent = button ? button.innerHTML : '';
    
    if (button) {
      button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
      button.disabled = true;
    }
    
    // Faire la requête à l'API Polly
    const response = await fetch('/espagnol/api/polly/speak', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: text,
        voice: options.voice || currentPollyVoice,
        language: language
      })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    // Convertir la réponse en audio
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    
    // Créer et jouer l'élément audio
    currentAudio = new Audio(audioUrl);
    
    // Mettre l'élément en surbrillance s'il est fourni
    const highlightElement = options.highlightElement || null;
    if (highlightElement) {
      highlightElement.classList.add('polly-highlight');
    }
    
    // Événement de fin de lecture
    currentAudio.onended = function() {
      currentAudio = null;
      // Nettoyer l'URL
      URL.revokeObjectURL(audioUrl);
      
      // Restaurer l'état du bouton
      if (button) {
        button.innerHTML = originalButtonContent;
        button.disabled = false;
      }
      
      // Supprimer la surbrillance
      if (highlightElement) {
        highlightElement.classList.remove('polly-highlight');
      }
      
      // Appeler le callback si fourni
      if (options.onEnd && typeof options.onEnd === 'function') {
        options.onEnd();
      }
    };
    
    // Événement d'erreur
    currentAudio.onerror = function(e) {
      console.error('Erreur de lecture audio:', e);
      currentAudio = null;
      URL.revokeObjectURL(audioUrl);
      
      if (button) {
        button.innerHTML = originalButtonContent;
        button.disabled = false;
      }
      
      if (highlightElement) {
        highlightElement.classList.remove('polly-highlight');
      }
    };
    
    // Lancer la lecture
    await currentAudio.play();
    
  } catch (error) {
    console.error('Erreur lors de la synthèse vocale:', error);
    alert('Erreur lors de la lecture audio. Veuillez réessayer.');
    
    // Restaurer l'état du bouton en cas d'erreur
    if (options.button) {
      options.button.innerHTML = '<i class="fa-solid fa-play"></i>';
      options.button.disabled = false;
    }
  }
}

/**
 * Fonction pour changer la voix Polly
 * @param {string} voice - ID de la voix (ex: Lucia, Enrique, etc.)
 */
function setPollyVoice(voice) {
  currentPollyVoice = voice;
  
  // Sauvegarder la préférence via une requête API
  fetch('/espagnol/api/voice-settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      voice_a: voice,
      voice_b: voice
    })
  })
  .then(response => {
    if (response.ok) {
      // Notification visuelle pour confirmer le changement
      const voiceSelector = document.getElementById('voice-selector');
      if (voiceSelector) {
        const originalBg = voiceSelector.style.backgroundColor;
        voiceSelector.style.backgroundColor = '#d4edda';
        setTimeout(() => {
          voiceSelector.style.backgroundColor = originalBg;
        }, 500);
      }
    }
  })
  .catch(error => {
    console.error('Erreur lors de la sauvegarde de la préférence de voix:', error);
  });
}

// Utilitaire pour détecter et lire tout texte marqué avec la classe 'polly-speak'
function initializePollyElements() {
  document.querySelectorAll('.polly-speak').forEach(element => {
    const playButton = document.createElement('button');
    playButton.className = 'btn btn-sm btn-outline-primary polly-btn';
    playButton.innerHTML = '<i class="fa-solid fa-play"></i>';
    playButton.title = 'Écouter avec Polly';
    
    // Déterminer la langue
    const lang = element.getAttribute('data-lang') || 'es-ES';
    
    playButton.addEventListener('click', () => {
      const text = element.textContent.trim();
      playPollyAudio(text, lang, {
        button: playButton,
        highlightElement: element
      });
    });
    
    // Ajouter le bouton après l'élément
    element.insertAdjacentElement('afterend', playButton);
  });
}

// Initialisation des éléments Polly lors du chargement de la page
document.addEventListener('DOMContentLoaded', initializePollyElements);
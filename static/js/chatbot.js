document.addEventListener('DOMContentLoaded', function () {
    const chatbotPanel = document.getElementById('chatbotPanel');
    const chatbotHeader = document.getElementById('chatbotHeader'); // For dragging, if implemented later
    const toggleChatbotButton = document.getElementById('toggleChatbotButton');
    const chatbotMessagesDiv = document.getElementById('chatbotMessages');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSendButton = document.getElementById('chatbotSendButton');

    let isChatbotOpen = true; // Assuming it starts open or visibility is controlled by CSS
    
    // Chatbot context variables
    let currentChatbotOriginalHeader = null;
    let currentChatbotMappedField = null;
    let currentChatbotFileElement = null;
    let currentChatbotFileIdentifier = null;

    // Function to toggle chatbot visibility
    window.toggleChatbot = function() {
        isChatbotOpen = !isChatbotOpen;
        if (chatbotPanel) {
            // Example: Toggle a class that controls visibility or display property
            chatbotPanel.classList.toggle('hidden');
        }
        if (toggleChatbotButton) {
            toggleChatbotButton.textContent = isChatbotOpen ? '–' : '+';
        }
    };

    // Function to open/show the chatbot panel
    window.openChatbotPanel = function() {
        if (chatbotPanel && chatbotPanel.classList.contains('hidden')) {
            chatbotPanel.classList.remove('hidden');
            isChatbotOpen = true;
            if (toggleChatbotButton) {
                toggleChatbotButton.textContent = '–';
            }
        }
    };

    // Chatbot context management functions
    window.setCurrentChatbotContext = function(originalHeader, mappedField, fileElement, fileIdentifier) {
        currentChatbotOriginalHeader = originalHeader;
        currentChatbotMappedField = mappedField;
        currentChatbotFileElement = fileElement;
        currentChatbotFileIdentifier = fileIdentifier;
        console.log('[Chatbot] Context set:', { originalHeader, mappedField, fileIdentifier });
    };

    window.getCurrentChatbotOriginalHeader = function() {
        return currentChatbotOriginalHeader;
    };

    window.clearCurrentChatbotOriginalHeader = function() {
        currentChatbotOriginalHeader = null;
        currentChatbotMappedField = null;
        currentChatbotFileElement = null;
        currentChatbotFileIdentifier = null;
        console.log('[Chatbot] Context cleared');
    };

    // Function to add a bot message (text or HTML element) to the chat
    window.addBotMessage = function(content) {
        if (chatbotMessagesDiv) {
            const messageContainer = document.createElement('div');
            messageContainer.classList.add('bot-message'); // This div gets the bot-message styling

            if (typeof content === 'string') {
                messageContainer.textContent = content;
            } else if (content instanceof HTMLElement) {
                // If content is an HTML element, append it directly.
                // The element itself can have its own styling (e.g. for suggestions).
                messageContainer.appendChild(content);
            } else {
                console.error("Invalid content type for addBotMessage:", content);
                return;
            }

            chatbotMessagesDiv.appendChild(messageContainer);
            chatbotMessagesDiv.scrollTop = chatbotMessagesDiv.scrollHeight; // Scroll to bottom
        }
    };

    // Function to add a user message to the chat
    window.addUserMessage = function(messageText) {
        if (chatbotMessagesDiv && messageText.trim() !== '') {
            const messageElement = document.createElement('div');
            messageElement.classList.add('user-message');
            messageElement.textContent = messageText;
            chatbotMessagesDiv.appendChild(messageElement);
            chatbotMessagesDiv.scrollTop = chatbotMessagesDiv.scrollHeight; // Scroll to bottom
        }
    };

    // Event listener for the toggle button
    if (toggleChatbotButton) {
        toggleChatbotButton.addEventListener('click', toggleChatbot);
    }

    // Event listener for the send button
    if (chatbotSendButton && chatbotInput) {
        chatbotSendButton.addEventListener('click', function () {
            const messageText = chatbotInput.value;
            if (messageText.trim() !== '') {
                addUserMessage(messageText);
                chatbotInput.value = ''; // Clear input after sending

                // Placeholder for sending message to backend or processing
                // For now, maybe a simple echo or canned response
                // setTimeout(() => addBotMessage(`You said: "${messageText}" (This is a placeholder response).`), 500);
            }
        });

        // Allow sending with Enter key in input field
        chatbotInput.addEventListener('keypress', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent default form submission if it were in a form
                chatbotSendButton.click();
            }
        });
    }

    // Example: Make chatbot panel initially appear closed if preferred
    // Ensure chatbot is visible if hidden, when this is called.
    window.promptToSaveTemplate = function(fileIdentifier) {
        if (typeof window.toggleChatbot === 'function' && chatbotPanel && chatbotPanel.classList.contains('hidden')) {
            window.toggleChatbot();
        }

        const promptMessageDiv = document.createElement('div');
        promptMessageDiv.className = 'save-template-prompt';

        const textNode = document.createTextNode(`You've made several changes to mappings for ${fileIdentifier}. Would you like to save these as a new template? `);
        promptMessageDiv.appendChild(textNode);

        const yesButton = document.createElement('button');
        yesButton.textContent = "Yes, Save Template";
        yesButton.className = "btn-save-template-yes"; // For styling and specific listener
        yesButton.setAttribute('data-file-identifier', fileIdentifier);
        promptMessageDiv.appendChild(yesButton);

        const noButton = document.createElement('button');
        noButton.textContent = "No, Thanks";
        noButton.className = "btn-save-template-no";
        promptMessageDiv.appendChild(noButton);

        addBotMessage(promptMessageDiv); // addBotMessage now handles HTML elements

        // No need to add listener here if using event delegation on chatbotMessagesDiv for these buttons
    };


    // Event listener for clicking on suggestion elements OR buttons within bot messages
    if (chatbotMessagesDiv) {
        chatbotMessagesDiv.addEventListener('click', function(event) {
            const targetElement = event.target;

            // Handle suggestion clicks
            const suggestionElement = targetElement.closest('.chatbot-suggestion');
            if (suggestionElement) {
                const suggestedField = suggestionElement.getAttribute('data-suggested-field');
                // Use the new setCurrentChatbotOriginalHeader/getCurrentChatbotOriginalHeader from upload.js context
                const originalHeader = window.getCurrentChatbotOriginalHeader ? window.getCurrentChatbotOriginalHeader() : null;


                if (suggestedField && originalHeader) {
                    const allSelects = document.querySelectorAll(`.mapped-field-select[data-original-header="${originalHeader}"]`);
                    if (allSelects.length > 0) {
                        allSelects.forEach(selectElement => {
                            selectElement.value = suggestedField;
                            selectElement.dispatchEvent(new Event('change'));
                        });
                        addBotMessage(`Okay, I've updated the mapping for "${originalHeader}" to "${suggestedField}".`);
                        if(window.clearCurrentChatbotOriginalHeader) window.clearCurrentChatbotOriginalHeader();
                    } else {
                        addBotMessage(`I couldn't find the dropdown for header "${originalHeader}" to update it.`);
                        console.error(`Could not find select element for original header: ${originalHeader}`);
                    }
                } else {
                    console.error("Missing suggested field or original header context.", {suggestedField, originalHeader});
                }
                return; // Processed suggestion click
            }

            // Handle "Yes, Save Template" button from chatbot prompt
            if (targetElement.classList.contains('btn-save-template-yes')) {
                const fileIdentifier = targetElement.getAttribute('data-file-identifier');
                const fileEntryElement = document.querySelector(`.file-entry[data-filename="${fileIdentifier}"]`);
                if (fileEntryElement && typeof window.triggerSaveTemplateWorkflow === 'function') {
                    addBotMessage("Okay, let's save that template...");
                    window.triggerSaveTemplateWorkflow(fileIdentifier, fileEntryElement); // Pass fileEntryElement as context
                    // Remove the prompt message after action (optional)
                    targetElement.closest('.save-template-prompt').remove();
                } else {
                    console.error("Could not trigger save workflow. File entry or function missing for:", fileIdentifier);
                    addBotMessage("Sorry, I couldn't start the save process. Please try using the main button.");
                }
                return; // Processed save confirmation
            }

            // Handle "No, Thanks" button from chatbot prompt
            if (targetElement.classList.contains('btn-save-template-no')) {
                addBotMessage("Okay, no problem!");
                // Remove the prompt message
                targetElement.closest('.save-template-prompt').remove();
                return; // Processed "no thanks"
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const chatbotPanel = document.getElementById('chatbotPanel');
    const chatbotHeader = document.getElementById('chatbotHeader'); // For dragging, if implemented later
    const toggleChatbotButton = document.getElementById('toggleChatbotButton');
    const chatbotMessagesDiv = document.getElementById('chatbotMessages');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSendButton = document.getElementById('chatbotSendButton');

    let isChatbotOpen = true; // Assuming it starts open or visibility is controlled by CSS

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
    // if (chatbotPanel) chatbotPanel.classList.add('hidden');
    // if (toggleChatbotButton) toggleChatbotButton.textContent = '+';
    // isChatbotOpen = false;


    // Event listener for clicking on suggestion elements
    if (chatbotMessagesDiv) {
        chatbotMessagesDiv.addEventListener('click', function(event) {
            const suggestionElement = event.target.closest('.chatbot-suggestion');
            if (suggestionElement) {
                const suggestedField = suggestionElement.getAttribute('data-suggested-field');
                const originalHeader = window.getCurrentChatbotOriginalHeader ? window.getCurrentChatbotOriginalHeader() : null;

                if (suggestedField && originalHeader) {
                    // Find the corresponding select element in the main document
                    // This assumes select elements have `data-original-header` attribute.
                    const allSelects = document.querySelectorAll(`.mapped-field-select[data-original-header="${originalHeader}"]`);

                    if (allSelects.length > 0) {
                        // There might be multiple files on the page, so we need to be careful if headers are not unique across files.
                        // For now, let's assume we are targeting the one relevant to the current interaction context.
                        // If multiple files can have identical original headers, a more specific selector would be needed,
                        // possibly involving the file index or a more unique ID on the select.
                        // For this example, we'll update the first one found, or all if that's desired.
                        allSelects.forEach(selectElement => {
                            selectElement.value = suggestedField;
                            // Trigger change event to update dependent things, like the 'data-current-mapped-field' on the help button
                            selectElement.dispatchEvent(new Event('change'));
                        });

                        addBotMessage(`Okay, I've updated the mapping for "${originalHeader}" to "${suggestedField}".`);

                        // Optionally, clear context and/or hide chatbot
                        if(window.clearCurrentChatbotOriginalHeader) window.clearCurrentChatbotOriginalHeader();
                        // if (isChatbotOpen) toggleChatbot(); // Optionally close chatbot

                    } else {
                        addBotMessage(`I couldn't find the dropdown for header "${originalHeader}" to update it.`);
                        console.error(`Could not find select element for original header: ${originalHeader}`);
                    }
                } else {
                    console.error("Missing suggested field or original header context for applying suggestion.", {suggestedField, originalHeader});
                }
            }
        });
    }
});

import React, { useState,useEffect, useRef,useContext } from 'react';
// import mermaid from 'mermaid';
import defaultQuestionsData from './defaultQuestions.json';

import { v4 as uuidv4 } from 'uuid';

import katex from 'katex';
import 'katex/dist/katex.min.css'; // Import KaTeX CSS

import { saveChatAsPDF } from './pdfUtils';
import { ChatContext } from './ChatContext';




function dataURLtoBlob(dataURL) {
    const [header, base64Data] = dataURL.split(',');
    const mime = header.match(/:(.*?);/)[1];
    const binary = atob(base64Data);
    const array = [];
    for (let i = 0; i < binary.length; i++) {
        array.push(binary.charCodeAt(i));
    }
    return new Blob([new Uint8Array(array)], { type: mime });
}

function Chatbot() {
    const { chatHistory, addMessage } = useContext(ChatContext);
    const [messages, setMessages] = useState([]);
    const [userMessage, setUserMessage] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    // const [defaultQuestionsData, setDefaultQuestions] = useState([]); // State for external options
    const chatWindowRef = useRef(null); // Create a ref for the chat window
    const [dropdownValue, setDropdownValue] = useState('general query'); // State for dropdown selection
    const [pastedImage, setPastedImage] = useState(null); // State for the pasted image
    const [isProcessing, setIsProcessing] = useState(false); // Track if image is being processed
    const [messageToSend, setMessageToSend] = useState(""); // Input field message
    const chatContainerRef = useRef(null);
    const [isScrolledUp, setIsScrolledUp] = useState(false);
    const [isUserAtBottom, setIsUserAtBottom] = useState(true);
    const [messageFeedback, setMessageFeedback] = useState({});
    const [sliderValue, setSliderValue] = useState(0.3); // Default value
    const [isAnsForVisible, setisAnsForVisible] = useState(false); // Dropdown visibility
    const [inputText, setInputText] = useState('');
    const [extractedText, setExtractedText] = useState('');
    const [chatMessages, setChatMessages] = useState([]);

    // Scroll handling
    useEffect(() => {
        const chatContainer = chatContainerRef.current;

        if (!chatContainer) return; // Ensure chatContainerRef.current is not null

        const handleScroll = () => {
            const { scrollTop, scrollHeight, clientHeight } = chatContainer;
            const atBottom = scrollTop + clientHeight >= scrollHeight-50; // 10px margin
            setIsUserAtBottom(atBottom);
        };

        chatContainer.addEventListener('scroll', handleScroll);

        // Initial check
        handleScroll();

        return () => {
            chatContainer.removeEventListener('scroll', handleScroll);
        };
    }, []);

    // Conditional auto-scroll
    useEffect(() => {
        if (isUserAtBottom && chatContainerRef.current) {
            chatContainerRef.current.scrollTo({
                top: chatContainerRef.current.scrollHeight,
                behavior: 'smooth',
            });
        }
    }, [messages, isTyping, isUserAtBottom]);

    const MessageFeedback = ({ messageId, onFeedback, feedbackType }) => {
        return (
            <div className="feedback-buttons">
                <button 
                    onClick={() => onFeedback(messageId, 'positive')}
                    className={`feedback-btn ${feedbackType === 'positive' ? 'positive-feedback' : ''}`}
                >
                    👍
                </button>
                <button 
                    onClick={() => onFeedback(messageId, 'negative')}
                    className={`feedback-btn ${feedbackType === 'negative' ? 'negative-feedback' : ''}`}
                >
                    👎
                </button>
            </div>
        );
    };

    // Hide sidebar when all selections are made or manually hidden
    const toggleAnswerFormat = () => {
        setisAnsForVisible(!isAnsForVisible);
    };

    const handleTextInputChange = (event) => {
        setInputText(event.target.value);
        // setExtractedText(event.target.value);
    };

    const handleFileUpload = async (event) => {
        console.log('File uploaded:', event.target.files[0]);
        const file = event.target.files[0];
        if (!file) return;

        try {
            const formData = new FormData();
            formData.append('file', file);

            // Send to backend for OCR processing
            const response = await fetch(`http://${window.location.hostname}:5000/ocr-image`, {
                method: 'POST',
                body: formData,
                credentials: 'include',
            });
            const data = await response.json();
            setInputText(data.ocr_text);
            // setExtractedText(data.ocr_text);
        } catch (error) {
            console.error('OCR processing failed:', error);
        }
    };

    const handleSliderChange = (e) => {
        const value = parseFloat(e.target.value);
        setSliderValue(value);
      };



      

    const handleFeedback = async  (messageId, feedbackType) => {

        const requestData = {
            feedback: feedbackType,
            u_id : messageId
        };
        try {
            // Send POST request
            const response = await fetch(`http://${window.location.hostname}:5000/submit-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData),
                credentials: 'include',
            });
    
            if (response.ok) {
                console.log('Feedback submitted successfully');
            } else {
                console.error('Failed to submit feedback');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
        }
        setMessageFeedback((prev) => ({
            ...prev,
            [messageId]: feedbackType, // Store the feedback for this specific message
        }));
    };
    
    
    
    const sendMessage = async (userMessage, buttonKey = null) => {
        
        const messageToSend = buttonKey ? buttonKey : userMessage; // Use button text if provided
        if (messageToSend.trim() || pastedImage) {
            const newMessages = [...messages, {sender: 'user', text: messageToSend }];
            // setMessages(newMessages);
            const u_id = uuidv4()
            // console.log('u_id value is:',u_id);
            setMessages((prevMessages) => [
                ...prevMessages,
                {id: u_id, sender: 'user', text: messageToSend },
            ]);
            addMessage({ sender: 'user', text: messageToSend }); // Update context
            setUserMessage('');
            setIsTyping(true);
            


            if (pastedImage) {
                
                const formData = new FormData();
                const blob = dataURLtoBlob(pastedImage);
                formData.append('image', blob);
            
                // Send the image to the backend for OCR processing
                fetch(`http://${window.location.hostname}:5000/chatbot`, {
                    method: 'POST',
                    body: formData,
                    credentials: 'include',
                })
                .then((response) => response.json())
                .then((data) => {
                    // Add the image and a processing message to the chat
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {id: uuidv4(), sender: 'user', image: pastedImage },
                        {id: uuidv4(), sender: 'bot', text: 'Processing image, please wait...' },
                    ]);
                    addMessage({ sender: 'user', text: messageToSend });
                    addMessage({ sender: 'bot', text: 'Processing image, please wait...' });
                    setPastedImage(null); // Clear the image preview
                    
                    // Extract OCR text from the response
                    const ocrText = data.ocr_text;
                    const u_id = uuidv4()
                    // Add OCR result to chat
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {id: u_id, sender: 'user', text: `OCR Result: ${ocrText}` },
                        // { sender: 'bot', text: `Here's your processed OCR text: ${ocrText}` },
                    ]);
                    addMessage({ sender: 'user', text: `OCR Result: ${ocrText}` });
            
                    // Send the OCR text back to the backend for a response
                    const requestData = {
                        message: ocrText,
                        dropdownOption: dropdownValue || null,
                        u_id : u_id,
                        temperature: sliderValue
                    };
            
                    return fetch(`http://${window.location.hostname}:5000/chatbot`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestData),
                        credentials: 'include',
                    });
                })
                .then((response) => response.json())
                .then((data) => {
                    const fullResponse = data.response;
                    let displayedText = '';
                    let index = 0;

                    
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {sender: 'bot', text: 'Typing your response...' } // Temporary message to simulate typing
                    ]);
                    addMessage({ sender: 'bot', text: 'Typing your response...' });
            
                    // Simulate typing effect for bot's response
                    const typingInterval = setInterval(() => {
                        displayedText += fullResponse[index];
                        setMessages((prevMessages) => {
                            const updatedMessages = [...prevMessages];
                            updatedMessages[updatedMessages.length - 1] = {sender: 'bot', text: displayedText };
                            return updatedMessages;
                        });
                        index += 1;
            
                        if (index === fullResponse.length) {
                            clearInterval(typingInterval);
                            addMessage({ sender: 'bot', text: fullResponse });
                            setIsTyping(false); // Stop typing indicator
                            setIsProcessing(false); // Re-enable input once typing is done
                        }
                    }, 10); // Adjust typing speed here
                })
                .catch((error) => {
                    console.error('Image upload or OCR error:', error);
                    setMessages((prevMessages) => [
                        ...prevMessages,
                        {id: uuidv4(), sender: 'bot', text: 'Failed to process the image.' },
                    ]);
                    addMessage({ sender: 'bot', text: 'Failed to process the image.' });
                    setIsTyping(false); // Stop typing indicator
                    setIsProcessing(false); // Re-enable input on error
                });
            }
            const requestData = {
                message: messageToSend,
                dropdownOption: dropdownValue || null,
                u_id : u_id,
                temperature: sliderValue
            };
            // Check for "flow chart" keyword
            if (userMessage.toLowerCase().includes("flow chart")) {
                // Fetch the flow chart image
                const imageResponse = await fetch(`http://${window.location.hostname}:5000/chatbot`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage }),
                    credentials: 'include'
                });

                // Convert the response to a Blob
                const imageBlob = await imageResponse.blob();
                

                const reader = new FileReader();
            reader.onloadend = () => {
                const base64Image = reader.result; // This is the base64 string of the image
                setMessages((prevMessages) => [
                    ...prevMessages,
                    {id: uuidv4(), sender: 'bot', image: base64Image }
                ]);
                addMessage({ sender: 'bot', image: base64Image });
                setIsTyping(false);
            };

            reader.readAsDataURL(imageBlob); // Convert the Blob to a base64 string

                
            } else {

            // Send the message to Flask backend           
            const response = await fetch(`http://${window.location.hostname}:5000/chatbot`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
                credentials: 'include'
            });

            
            const data = await response.json();
            // const botMessage = data.response;

            const fullResponse = data.response;
             // Simulate typing effect
             const simulateTypingEffect = (fullResponse) => {
                let displayedText = '';
                let index = 0;
            
                setIsTyping(true);
            
                const typingInterval = setInterval(() => {
                    if (index < fullResponse.length) {
                        displayedText += fullResponse[index];
                        setMessages((prevMessages) => {
                            const updatedMessages = [...prevMessages];
                            const lastMessage = updatedMessages[updatedMessages.length - 1];
                            if (lastMessage.sender === 'bot') {
                                updatedMessages[updatedMessages.length - 1] = {sender: 'bot', text: displayedText };
                            } else {
                                // Safety check: Add a new bot message if last message is not from bot
                                updatedMessages.push({sender: 'bot', text: displayedText });
                            }
                            return updatedMessages;
                        });
                        index += 1;
                    } else {
                        clearInterval(typingInterval);
                        setIsTyping(false);
                        // Ensure the full message is set
                        setMessages((prevMessages) => {
                            const updatedMessages = [...prevMessages];
                            const lastMessage = updatedMessages[updatedMessages.length - 1];
                            if (lastMessage.sender === 'bot') {
                                updatedMessages[updatedMessages.length - 1] = {id: u_id, sender: 'bot', text: fullResponse };
                            }
                            return updatedMessages;
                        });
                        addMessage({ sender: 'bot', text: fullResponse }); // Update context
                    }
                }, 10); // Adjust typing speed here (e.g., 30ms per character)
            };
             
            setMessages((prevMessages) => [
                ...prevMessages,
                {sender: 'bot', text: "Typing..." },
            ]);

            // addMessage({ sender: 'bot', text: fullResponse });
            simulateTypingEffect(fullResponse);
            

            }
            // setMessages([...newMessages, { sender: 'bot', text: botMessage }]);
        }
        
    };
    const handlePaste = (event) => {
        
        const items = event.clipboardData.items;
        for (let item of items) {
            if (item.type.startsWith('image/')) {
                const blob = item.getAsFile();
                const reader = new FileReader(); // Create a new FileReader instance

                reader.onloadend = () => {
                    // Once the file is read, `reader.result` contains the base64-encoded image
                    const base64Image = reader.result; // This is the base64 string of the image
                    setPastedImage(base64Image); // Set the image preview
                    
                };

                // Read the image file as a base64-encoded string
                reader.readAsDataURL(blob);
                // Optionally, prevent default behavior (if you want to stop it from being pasted as an image file)
                event.preventDefault();
                
                setIsProcessing(true);
                return;
            }
        }
    };

    // This useEffect will run every time messages change
    useEffect(() => {
        if (isUserAtBottom && chatWindowRef.current) {
            chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
        }
    }, [messages]);

    
    const renderMessage = (text) => {
        if (typeof text !== 'string') {
            console.error('Expected a string but got:', typeof text);
            return <span>{text}</span>;
        }
    
        // Function to replace LaTeX syntax with rendered HTML using KaTeX
        const renderLaTeX = (content) => {
            return content.replace(/(\\\((.*?)\\\))|(\$\$(.*?)\$\$)|\\\[([\s\S]*?)\\\]/gs, (match, inlineMath, inlineContent, blockMath, blockContent, multilineContent) => {
                const latex = inlineContent || blockContent || inlineMath || blockMath || multilineContent;
                // const displayMode = !!blockMath; 
                try {
                    return katex.renderToString(latex, { throwOnError: false });
                } catch (error) {
                    console.error('Error rendering LaTeX:', error);
                    return match;
                }
            });

        };
    
        // Function to handle Markdown headers and bold text
        const handleMarkdown = (line) => {
            // Check for Markdown headers (e.g., # or ##)
            if (line.startsWith('# ')) {
                return `<strong style="font-size: 1.2em;">${line.slice(2)}</strong>`; // For H1-style headers
            } else if (line.startsWith('## ')) {
                return `<strong style="font-size: 1.1em;">${line.slice(3)}</strong>`; // For H2-style headers
            }
            else if (line.startsWith('### ')) {
                return `<strong style="font-size: 1.1em;">${line.slice(3)}</strong>`; // For H2-style headers
            }

            line = line.replace(/\*\*(.*?)\*\*/gs, (match, p1) => {
                return `<strong>${p1}</strong>`; // Wrap bolded text in <strong> tags
            });

            // line = line.replace(/\[(.*?)\]/gs, (match, p1) => {
            //     return `<strong>${p1}</strong>`; // Wrap bolded text in <strong> tags
            // });

            // line = line.replace(/\((.*?)\)/gs, (match, p1) => {
            //     return `<strong>${p1}</strong>`; // Wrap bolded text in <strong> tags
            // });


    
            // Check for bold text using Markdown syntax (e.g., **bolded text**)
            return line
            
        };
        // Function to make URLs clickable
        const makeHyperlinks = (content) => {
            const urlRegex = /(https?:\/\/[^\s()]+(?:\([^\s()]*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))/g;
            return content.replace(urlRegex, (url) => {
                return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
            });
        };
    
        // Split the text into lines based on newlines and render
    const lines = text.split(/\r?\n/);

    // const lines = text;

    return lines.map((line, i) => {
        // Handle Markdown and LaTeX for each line
        const htmlContent = handleMarkdown(line); // Handle markdown (headers, bold, etc.)

        // Apply LaTeX rendering to the content
        const htmlWithLaTeX = renderLaTeX(htmlContent);
        const textWithLinks = makeHyperlinks(htmlWithLaTeX); // Add hyperlinks

        return <span key={i} dangerouslySetInnerHTML={{ __html: textWithLinks + '<br />'}} />;
        });
    };

    


    return (
        
        <div className="chatbot-container">
            <div>
            {/* <h2 className="chatbot-title">MBUE</h2> */}
            {/* <h2 className="selected-chapter"></h2> */}
            <button onClick={() => saveChatAsPDF(messages)} className="save-pdf-button">
                Save Chat as PDF
            </button>
            </div>

            <div className="chat-window" ref={chatContainerRef}>
                {messages.map((msg, index) => (
                    <div key={msg.id} className={msg.sender === 'user' ? 'user-message' : 'bot-message'}>
                        {msg.text && renderMessage(msg.text)}                        
                        {msg.image && (
                        <div>
                        {/* Clickable image to open in a new tab */}
                        <a 
                            href={msg.image} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            onClick={(e) => {
                                e.preventDefault(); // Prevent default navigation
                                const blob = dataURLtoBlob(msg.image);
                                const blobURL = URL.createObjectURL(blob); // Create a Blob URL
                                const newWindow = window.open(blobURL, '_blank');
                                if (newWindow) newWindow.opener = null; // Security
                            }}
                        >
                            <img src={msg.image} alt="Flowchart" className="flowchart-image" />
                        </a>

                        {/* Download and Open Flowchart */}
                        <a
                            href={msg.image}
                            download="flowchart.png"
                            className="download-link"
                            onClick={(e) => {
                                e.preventDefault(); // Prevent default behavior
                                const blob = dataURLtoBlob(msg.image);
                                const blobURL = URL.createObjectURL(blob); // Create a Blob URL
                                
                                // Trigger download
                                const link = document.createElement('a');
                                link.href = blobURL;
                                link.download = 'flowchart.png';
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);

                                // Open the image in a new tab after download
                                const newWindow = window.open(blobURL, '_blank');
                                if (newWindow) newWindow.opener = null;
                            }}
                        >
                            Download and Open
                        </a>
                        </div>
                        )}
                        {msg.sender === 'bot' && (
                            <MessageFeedback 
                              messageId={msg.id}
                              onFeedback={handleFeedback}
                              feedbackType={messageFeedback[msg.id]}
                            />
                          )}  
                        </div>
                            
                          
                        ))}
                        {isTyping && <div className="bot-message typing-indicator">Typing<span className="dot">.</span><span className="dot">.</span><span className="dot">.</span></div>}
            </div>
            
            <div className="bottom-section ">
            <div className="dropdown-container">
                    <div className="dropdown-only">
                <label >What do you want to do:</label>
                <select
                    id="dropdown"
                    value={dropdownValue}
                    onChange={(e) => setDropdownValue(e.target.value)}
                >
                    <option value="general query">General Query</option>
                    {/* <option value="answer the question">answer the question</option> */}
                    {/* <option value="Correct the answer">Correct the answer</option> */}
                    {/* <option value="Help me remember">Help me remember</option> */}
                    {/* <option value="Rewrite in simple words">Rewrite in simple words</option>                     */}
                    <option value="Use gpt-4o">Use gpt-4o</option>
                    {/* <option value="I did not understand">I did not understand</option> */}
                </select>
                </div>
            

            {/* <div style={{  alignItems: "center", width: "600px", margin: "0 auto", textAlign: "center" }}> */}
            {/* <div style={{ justifyContent: "space-between" }}> */}
            <div className="slider-only-container">
                <span>Exact Answer</span>
                
            {/* </div> */}
            <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={sliderValue}
                onChange={handleSliderChange}
                // style={{ width: "100%" }}
            />

            {/* <div style={{ display: "flex", justifyContent: "space-between" }}> */}
            <span>Creative Answer</span>
            {/* </div> */}

            <h2>Current Value: {sliderValue}</h2>
            {/* </div> */}
            </div>
            <div className={`answer-format ${isAnsForVisible ? 'visible' : 'hidden'}`}>
                <button className="toggle-answer-format-btn" onClick={toggleAnswerFormat}>
                    {isAnsForVisible ? 'Hide' : 'Answer Format Options'}
                </button>

                {isAnsForVisible && (
                    <div className="answer-format-options">
                        <textarea
                            className="text-input"
                            placeholder="Paste text here..."
                            value={inputText}
                            onChange={handleTextInputChange}
                        ></textarea>

                        <div className="file-upload">
                            <label htmlFor="file-upload-input">Or Upload Image:</label>
                            <input
                                type="file"
                                id="file-upload-input"
                                accept="image/*, application/pdf"
                                onChange={handleFileUpload}
                            />
                        </div>

                        {/* {extractedText && (
                            <div className="ocr-result">
                                <h4>Extracted Text:</h4>
                                <p>{extractedText}</p>
                            </div>
                        )} */}

                        {/* <button className="submit-query-btn" onClick={handleQuerySubmit}>
                            Submit Query
                        </button> */}
                    </div>
                )}
            </div>
            
            

            </div>      
            
            <div className="chat-space">
            {pastedImage && (
                    <div className="image-preview-container">
                        <div className="image-preview">
                            <img src={pastedImage} alt="Pasted Preview" className="pasted-image" />
                            <button 
                            className="cancel-button" 
                            onClick={() => {
                                setPastedImage(null);
                                setIsProcessing(false);}}>
                                ✖
                            </button>
                        </div>
                    </div>
                )}
            <input
                type="text"
                value={userMessage}
                // disabled={isProcessing}  // Disable input if isProcessing is true
                readOnly={isProcessing}
                onChange={(e) => setUserMessage(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault(); // Prevent the default action (e.g., form submission)
                        sendMessage(userMessage); // Call the sendMessage function
                        setIsUserAtBottom(true);
                    }
                }}
                onPaste={handlePaste} // Handle pasted images                
                placeholder="Type your message or paste an image..."
                className="chat-input"
            />
            

            <button 
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault(); // Prevent the default action (e.g., form submission)
                        sendMessage(userMessage); // Call the sendMessage function
                        setIsUserAtBottom(true);
                    }
                }} 
                onClick={() => {sendMessage(userMessage);
                    setIsUserAtBottom(true);}
                } 
                className="send-button">Send</button>

            </div>

            <div className="default-options">
            {Object.keys(defaultQuestionsData).map((key, index) => (
            <button
                key={index}
                onClick={() => {sendMessage(defaultQuestionsData[key],key)
                    setIsUserAtBottom(true);}
                }
                className="option-button"
            >
                {key}
            </button>
            ))}

            </div>
            
            
        </div>

            
        </div>
        
    );
}

export default Chatbot;

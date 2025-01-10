import React, { useState, useEffect,useRef } from 'react';
import Chatbot from './components/Chatbot';
import S3Manager from './components/listFolder';
import './App.css';
import { ChatProvider } from './components/ChatContext'; // Path to your ChatContext
import axios from 'axios';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import '@react-pdf-viewer/core/lib/styles/index.css';


function App() {
    const [isWidgetOpen, setIsWidgetOpen] = useState(true); // State to control widget visibility
    
    const [isFullScreen, setIsFullScreen] = useState(true); // State to toggle full-screen mode
    const [pdfUrl, setPdfUrl] = useState(null); // State to hold the PDF URL
    const [isPdfVisible, setIsPdfVisible] = useState(false); // State to control PDF visibility
    const [name, setName] = useState(''); // State to hold the user's name
    const [isNameProvided, setIsNameProvided] = useState(false); // Name check
    const [isSidebarVisible, setIsSidebarVisible] = useState(true); // Dropdown visibility
    const [selectedGrades, setSelectedGrades] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedTopic, setSelectedTopic] = useState('');
    const [selectedChapter, setSelectedChapter] = useState('');
    const [nameInput, setNameInput] = useState(''); // State to hold the name input
    const iframeRef = useRef(null); // Reference to the iframe
    const [selectedFile, setSelectedFile] = useState(null);
    const [loading, setLoading] = useState(false);  // Track loading state
    const [filename, setFilename] = useState(''); // Track the file name input by the user
    
    const s3ManagerRef = useRef(null);
    const [selectedFiles, setSelectedFiles] = useState([]); // State for multiple files



    const handleFileUpload = (event) => {
        const files = Array.from(event.target.files); // Convert FileList to array
        const filesWithNames = files.map((file) => ({
            file,
            filename: file.name, // Default filename is the original file name
        }));
        setSelectedFiles(filesWithNames);
    };
    


    const handleFilenameChange = (index, newFilename) => {
        setSelectedFiles((prevFiles) =>
            prevFiles.map((file, idx) =>
                idx === index ? { ...file, filename: newFilename } : file
            )
        );
    };
    

    const uploadFiles = async () => {
        if (selectedFiles.length === 0) {
            alert('Please select files to upload.');
            return;
        }
    
        setLoading(true);
    
        try {
            for (const { file, filename } of selectedFiles) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('filename', filename);
    
                const response = await fetch(`http://${window.location.hostname}:5000/upload-file`, {
                    method: 'POST',
                    body: formData,
                    credentials: 'include',
                });
    
                const data = await response.json();
    
                if (!response.ok) {
                    alert(`Error uploading ${filename}: ${data.error}`);
                    continue; // Proceed with the next file
                }
    
                console.log('File uploaded:', filename, 'Folder:', data.folder);
                s3ManagerRef.current?.fetchFolders(data.folder); // Refresh folder list
            }
    
            alert('All files uploaded successfully!');
        } catch (error) {
            console.error('Error uploading files:', error);
            alert('Failed to upload some files.');
        } finally {
            setLoading(false);
            setSelectedFiles([]);
            document.getElementById('file-upload').value = '';
        }
    };

    
    
    // Toggle chat widget visibility
    const toggleWidget = () => {
        setIsWidgetOpen(!isWidgetOpen);
    };

    // Toggle PDF viewer visibility
    const togglePdfViewer = () => {
        setIsPdfVisible(!isPdfVisible);
    };

    
   // Save the scroll position to localStorage when user scrolls
  const handleScroll = () => {
    if (iframeRef.current) {
      const iframeDocument = iframeRef.current.contentWindow.document;
      const scrollPosition = iframeDocument.documentElement.scrollTop || iframeDocument.body.scrollTop;
      localStorage.setItem('pdfScrollPosition', scrollPosition); // Save scroll position
    }
  };

  // Restore the scroll position from localStorage when the component mounts
  useEffect(() => {
    const savedScrollPosition = localStorage.getItem('pdfScrollPosition');
    if (savedScrollPosition && iframeRef.current) {
      const iframeDocument = iframeRef.current.contentWindow.document;
      iframeDocument.documentElement.scrollTop = savedScrollPosition; // Restore scroll position
      iframeDocument.body.scrollTop = savedScrollPosition;
    }
  }, []);


    // Hide sidebar when all selections are made
    const hideSidebar = () => {
        setIsSidebarVisible(false);
    };

    // Hide sidebar when all selections are made or manually hidden
    const toggleSidebar = () => {
        // const currentPath = s3ManagerRef.current?.getCurrentPath(); 
        setIsSidebarVisible(!isSidebarVisible);
        
        // console.log("Fetching folders for current path:", currentPath);
        s3ManagerRef.current?.fetchFolders('');
    };



    

    const handlePdfUrlUpdate = (newPdfUrl) => {
        setPdfUrl(newPdfUrl);
        setIsPdfVisible(true);
    };

    // Toggle full-screen mode
    const toggleFullScreen = () => {
        setIsFullScreen(!isFullScreen);
    };

    // Function to handle name submission
    const handleNameSubmit = async () => {
        if (nameInput.trim() === '') {
            alert('Name is required to proceed.');
            return;
        }

        setName(nameInput);
        setIsNameProvided(true);




        // Send the name to the Flask backend
        try {
            const response = await fetch(`http://${window.location.hostname}:5000/submit-name`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: nameInput }),
                credentials: 'include'
            });

            if(response.ok){
                s3ManagerRef.current?.fetchFolders();

            
            }


            if (!response.ok) {
                throw new Error('Failed to submit name.');
            }
        } catch (error) {
            console.error('Error submitting name:', error);
        }
    };



    useEffect(() => {
        if (pdfUrl) {
            setIsSidebarVisible(false);
        }
    }, [pdfUrl]);


    return (
        <div className={`chat-widget ${isFullScreen ? 'full-screen' : ''}`}>
            
            
            {isWidgetOpen && (
                <div className={`widget-container ${isPdfVisible ? 'blurred' : ''}`}>
                    {!isNameProvided && (
                        <div className="modal">
                            <div className="modal-content">
                                <h2>Welcome! Please enter your name</h2>
                                <input
                                    type="text"
                                    value={nameInput}                            
                                    onChange={(e) => setNameInput(e.target.value)}
                                    placeholder="Enter your name"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            handleNameSubmit(); // Trigger submit on Enter key press
                                        }
                                    }}
                                />
                                <button onClick={handleNameSubmit}>Submit</button>
                            </div>
                        </div>
                    )}

                    <div className="widget-header">
                        <h2>Chatbot</h2>
                        
                        <div className="action-buttons">
                        {/* Button to toggle sidebar visibility */}
                        <button className="toggle-sidebar-btn" onClick={toggleSidebar}>
                            {isSidebarVisible ? 'Hide Selection Panel' : 'Show Selection Panel'}
                        </button>
                        </div>
                        
                        


                    </div>

                    
                    {isSidebarVisible && isNameProvided && (
                        <div className="selection-modal">
                        <div className="selection-modal-content">
                        
                            
                            <div className="upload-section">
                            
                            <div className="upload-cont">
                            
                            <label htmlFor="file-upload" className="custom-file-upload">
                            {selectedFile ? "File selected" : "Choose File to Upload"}
                            </label>

                            <input
                                type="file"
                                id="file-upload"
                                className="file-input"
                                accept=".pdf,.txt,.jpg,.jpeg,.png,.doc,.docx"
                                onChange={handleFileUpload}
                                multiple
                            />
                            

                            {selectedFiles.length > 0 && (
                                    <div className="file-list">
                                        <h2>Rename Files (optional)</h2> 
                                        {selectedFiles.map((fileData, index) => (
                                            <div key={index} className="file-item">
                                                <span>{fileData.file.name}</span>
                                                
                                                <input
                                                    type="text"
                                                    value={fileData.filename}
                                                    onChange={(e) => handleFilenameChange(index, e.target.value)}
                                                    placeholder="Enter new file name"
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {selectedFiles.length > 0 && (
                                    <button
                                        className="upload-btn"
                                        onClick={uploadFiles}
                                        disabled={loading}
                                    >
                                        {loading ? 'Uploading...' : 'UPLOAD FILES'}
                                    </button>
                                )}
                                {loading && (
                                    <div className="spinner-container">
                                        <div className="spinner"></div>
                                    </div>
                                )}
                            </div>
                            </div>

                            <S3Manager
                                ref={s3ManagerRef}
                                setPdfUrl={setPdfUrl}
                                hideSidebar={() => setIsSidebarVisible(false)} 
                            />

                            <button className="close-selection-btn" onClick={() => setIsSidebarVisible(false)}>
                                Close
                            </button>
                            </div>
                        </div>
                    )} 

                    {/* Display the selected chapter name or ask to select one */}
                    <div className="chapter-container">
                    {pdfUrl ? (
                        <h2 className="selected-chapter">{`File: ${pdfUrl[0].split('?')[0].split('/').at(-1)}`}</h2>
                    ) : (
                        <h2 className="selected-chapter">Please select a file to proceed.</h2>
                    )}
                    {/* {pdfUrl && selectedChapter && ( */}
                    {pdfUrl && (
                        <div className="show-pdf-btn-container">
                            <button className="show-pdf-btn" onClick={togglePdfViewer}>
                                Show PDF Viewer
                            </button>
                        </div>
                    )}                  

                    </div>
                    <div className="widget-body">
                    
                    <ChatProvider>
                        <Chatbot />
                    </ChatProvider>
                    </div>
                </div>
            )}

            {isPdfVisible && pdfUrl && (
            <div className="pdf-modal">
            <iframe
            ref={iframeRef}
            src={pdfUrl[0]}
            width="80%"
            height="80%"
            onLoad={() => {
              // When the iframe is loaded, add scroll event listener
              iframeRef.current.contentWindow.addEventListener('scroll', handleScroll);
            }}
            style={{ border: 'none' }}
          />
        
            <button className="pdf-modal-close-btn" onClick={togglePdfViewer}>
                ×
            </button>
            
        </div>
        )}
        </div>
    );
}

export default App;

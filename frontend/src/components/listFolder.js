import React, {useImperativeHandle, forwardRef, useState, useEffect } from 'react';
import axios from 'axios';
import { Document, Page, pdfjs } from 'react-pdf';
pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

const S3Manager = forwardRef( ({setPdfUrl},ref) => {
    const [folders, setFolders] = useState([]);
    const [files, setFiles] = useState([]);
    // const [pdfUrl, setPdfUrl] = useState('');
    const [pdfView, setPdfView] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [currentPath, setCurrentPath] = useState(''); // Tracks the current folder path
    const [newFolderName, setNewFolderName] = useState('');
    const [selectedFileKeys, setSelectedFileKeys] = useState([]);  // Store selected file keys
    const [selectedFiles, setSelectedFiles] = useState([]);

    // Handle checkbox change (track selected files)
    const handleCheckboxChange = (e) => {
        const { value, checked } = e.target;

        if (checked) {
            setSelectedFiles((prev) => [...prev, value]);  // Add key to selected if checked
        } else {
            setSelectedFiles((prev) => prev.filter((key) => key !== value));  // Remove key if unchecked
        }
    };

    const handleSelectAll = () => {
        if (selectedFiles.length === files.length) {
            setSelectedFiles([]); // Deselect all if all are selected
        } else {
            setSelectedFiles([...files]); // Select all
        }
    };

    // const [files, setFiles] = useState([]);

    const handleLoadError = (error) => {
      setErrorMessage(`Error loading PDF: ${error.message}`);
  };

  const handleSourceError = (error) => {
      setErrorMessage(`Source error: ${error.message}`);
  };

  useImperativeHandle(ref, () => ({
    fetchFolders, // Expose fetchFolders to the parent component via the ref
}));

// useImperativeHandle(ref, () => ({
//     fetchFolders(path) {
//         // Logic to fetch folders based on the given path
//         console.log(`Fetching folders for path: ${path || currentPath}`);
//     },
//     getCurrentPath() {
//         return currentPath; // Expose currentPath to parent
//     },
// }));

    useEffect(() => {
        fetchFolders();
    }, []);

    const fetchFolders = async (prefix = '') => {
        const resolvedPrefix = prefix === '/' ? '' : prefix; // Ensure root path fetches with empty prefix
        const response = await axios.get(`http://${window.location.hostname}:5000/list-folders`, {
            params: { prefix: resolvedPrefix },
            withCredentials: true 
        });
        // console.log("Entered fetchFolders");
        setFolders(response.data.folders);
        setFiles(response.data.files);
        setCurrentPath(resolvedPrefix); // Update the current path
        // console.log("Current path:", resolvedPrefix);
    };
    const prefixes = ["ncert", "cbse", "icse"];
    const createFolder = async (folderName) => {
        try {
            // if (prefixes.some(prefix => currentPath.startsWith(prefix)))
            //     {   alert("Cannot create Folder here. Use your personal folder to customize");
            //         console.log('Error creating folder:');
            //     }
            // else{
            // console.log("Current path during creation:", currentPath);   
            const sanitizedCurrentPath = currentPath.endsWith('/') && currentPath !== '/' 
            ? currentPath.slice(0, -1) 
            : currentPath;
            const fullFolderPath = `${sanitizedCurrentPath}${sanitizedCurrentPath ? '/' : ''}${folderName}`;
            // console.log("full path:", fullFolderPath);  
            await axios.post(`http://${window.location.hostname}:5000/create-folder`, {
                folder_name: fullFolderPath,
                
            },
            {withCredentials: true});
            
            fetchFolders(currentPath); // Refresh folder list
        // }
        
        setNewFolderName(''); // Clear the input field
        } catch (error) {
            console.error('Error creating folder:', error.message);
        }
    };

//     const selectFile = async (fileKey) => {
//       try {
//           // Dynamically construct the API URL
//           const response = await axios.get(`http://${window.location.hostname}:5000/select-file`, {
//               params: { file_key: fileKey }
//           ,
//           withCredentials: true });
          
  
//           // Ensure the response contains the URL
//           if (response.data.url) {
//               setPdfUrl(response.data.url);
//               setPdfView(true); // Show PDF viewer
//               console.log("Selected file:", response.data);
//           } else {
//               console.error("File URL not provided in response");
//           }
//       } catch (error) {
//           console.error("Error selecting file:", error.message);
//       }
//   };

    const selectFile = async (fileKeys) => {
        try {
            // Dynamically construct the API URL, pass fileKeys as a comma-separated string
            const response = await axios.post(`http://${window.location.hostname}:5000/select-file`,
                { file_keys: fileKeys.join(',') }, // Joining the file keys as a string
                {withCredentials: true}
            );

            // Ensure the response contains URLs
            if (response.data.urls && Array.isArray(response.data.urls)) {
                setPdfUrl(response.data.urls);  // Assume you have a state to hold URLs
                setPdfView(true); // Show PDF viewer for multiple files
                console.log("Selected files:", response.data.urls);
            } else {
                console.error("No URLs provided in response");
            }
        } catch (error) {
            console.error("Error selecting files:", error.message);
        }
    };

  const navigateUp = () => {
    // Ensure correct navigation for root and subfolders
    const newPath = currentPath
        ? currentPath.split('/').slice(0, -2).join('/') + '/'
        : ''; // Go back to root when at the top
    fetchFolders(newPath);
};

const handleSubmit = () => {
    if (selectedFiles.length === 0) {
        alert("Please select at least one file.");
        return;
    }
    selectFile(selectedFiles); // Pass the selected file keys to the API
};
    return (
        <div className="s3-manager">
            <h1>File Manager</h1>
            <div className="breadcrumb">
                <span className="current-path">Current Path: {currentPath || '/'}</span>
                {currentPath && <button onClick={navigateUp}>Go Back</button>}
            </div>
            <div className="folder-container">
                <h3>Folders</h3>
                <div className="folder-list">
                    {folders.map(folder => (
                        <div className="folder-item" key={folder} onClick={() => fetchFolders(folder)}>
                            📁 {folder}
                        </div>
                    ))}
                    <input
                        type="text"
                        placeholder="create new folder"
                        value={newFolderName}
                        onChange={(e) => setNewFolderName(e.target.value)} // Update state on change
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') createFolder(e.target.value);
                        }}
                    />
                </div>
            </div>
            {/* <div className="file-container">
                <h3>Files</h3>
                <div className="file-list">
                    {files.map(file => (
                        <div className="file-item" key={file} onClick={() => selectFile(file)}>
                            📄 {file}
                        </div>
                    ))}
                </div>
            </div> */}

            <div className="file-container">
                <h3>Files</h3>
                {files.length > 0 ? (
                    <div>
                    <div className="file-actions">
                        <button onClick={handleSelectAll}>
                            {selectedFiles.length === files.length ? "Deselect All" : "Select All"}
                        </button>
                    </div>
                    <div className="file-list">
                        {files.map((file) => (
                            <div className="file-item-2" key={file}>
                                <input 
                                    type="checkbox" 
                                    value={file} 
                                    onChange={handleCheckboxChange} 
                                    checked={selectedFiles.includes(file)}
                                />
                                📄 {file.split('/').pop()}
                            </div>
                        ))}
                    </div>
                    </div>
                ) : (
                    <p className="no-files">No files available</p>
                )}
                {/* <div className="bottom-section">
                    <p>Selected Files: {selectedFiles.length > 0 ? selectedFiles.map((file) => file.split("/").pop()).join(", ") : "None"}</p>
                    <button>Submit</button>
                </div> */}
            </div>

            <button onClick={handleSubmit}>Select Files</button>
            {/* {pdfView && (
                <div>
                    <h3>PDF Viewer</h3> */}
                    {/* <Document 
                    file={selectedFileUrl}
                    onLoadError={handleLoadError}
                    onSourceError={handleSourceError}>
                        <Page pageNumber={1} />
                    </Document> */}
                    {/* <iframe
                    src={selectedFileUrl}
                    width="100%"
                    height="600px"
                    title="PDF Viewer"
                    frameBorder="0"
                    style={{border: 'none'}}
                /> */}
                    {/* <Document file="https://www.w3.org/WAI/WCAG21/quickref/files/pdf/wcag-quickref-20.pdf">
                      <Page pageNumber={1} />
                  </Document> */}
                {/* </div>
            )} */}
        </div>
    );
});


export default S3Manager;

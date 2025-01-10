
import { jsPDF } from 'jspdf'; // Import jsPDF


export const saveChatAsPDF = async (messages, filename = 'chat.pdf') => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.width;
    const pageHeight = doc.internal.pageSize.height;
    const margin = 10; // Left margin for text
    let yPosition = 10; // Initial y position

    // Set font size for text content
    const fontSize = 12; 
    const lineHeightFactor = 1.15; // Line height multiplier for spacing
    doc.setFontSize(fontSize);

    const maxImageWidth = 180; // Maximum allowed width in PDF
    const maxImageHeight = 160; // Maximum allowed height in PDF

    const getImageDimensions = (base64Image) => {
        return new Promise((resolve) => {
            const img = new Image();
            img.src = base64Image;
            img.onload = () => {
                resolve({ width: img.naturalWidth, height: img.naturalHeight });
            };
        });
    };

    for (const msg of messages) {
        console.log(msg)
        const textContent = msg.text || '';
        const sender = msg.sender || '';
        const imageContent = msg.image || '';

        // Handle sender info
        if (sender) {
            const maxWidth = pageWidth - margin * 2; // Max width for text
            const senderText = doc.splitTextToSize(sender, maxWidth);
            const lineHeight = doc.getTextDimensions('Test').h * lineHeightFactor; // Single-line height
            const textHeight = senderText.length * lineHeight;
            

            // Check if text will overflow the page
            if (yPosition + textHeight > pageHeight - margin) {
                doc.addPage(); // Add new page
                yPosition = margin; // Reset yPosition to top of the new page
            }

            
            doc.setFont('Helvetica', 'bold')
            doc.text(senderText, margin, yPosition);
            yPosition += textHeight + 10; // Adjust position after the text

            
        }

        // Handle text content
        if (textContent) {
            const maxWidth = pageWidth - margin * 2; // Max width for text
            const wrappedText = doc.splitTextToSize(textContent, maxWidth);
            const lineHeight = doc.getTextDimensions('Test').h * lineHeightFactor; // Single-line height
            const textHeight = wrappedText.length * lineHeight;
            

            // Check if text will overflow the page
            if (yPosition + textHeight > pageHeight - margin) {
                doc.addPage(); // Add new page
                yPosition = margin; // Reset yPosition to top of the new page
            }

            
            doc.setFont('Helvetica', 'normal')
            doc.text(wrappedText, margin, yPosition);
            yPosition += textHeight + 10; // Adjust position after the text

            
        }

        // Handle image content
        if (imageContent) {
            // const base64Image = imageContent.replace(/^data:image\/(png|jpg);base64,/, ''); // Strip prefix
            const { width: originalWidth, height: originalHeight } = await getImageDimensions(imageContent);
            console.log(originalHeight)
            console.log(originalWidth)
            const aspectRatio = originalWidth / originalHeight;
            console.log(aspectRatio)
            let imageWidth = Math.min(maxImageWidth, originalWidth);
            let imageHeight = imageWidth / aspectRatio;

            if (imageHeight > maxImageHeight) {
                imageHeight = maxImageHeight;
                imageWidth = imageHeight * aspectRatio;
            }

            console.log(imageHeight)
            console.log(imageWidth)

            // Check if image fits on the page
            if (yPosition + imageHeight > pageHeight - margin) {
                doc.addPage(); // Add new page
                yPosition = margin; // Reset yPosition
            }

            doc.addImage(imageContent, 'PNG', margin, yPosition, imageWidth, imageHeight); // Add image
            yPosition += imageHeight + 10; // Adjust position after the image
        }
    }

    doc.save('chat.pdf');
};
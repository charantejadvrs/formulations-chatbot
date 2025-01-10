# Use an official Node.js runtime as a parent image
FROM node:16 as build

# Set the working directory to /app
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install
# RUN npm install better-react-mathjax
RUN npm install katex
RUN npm install axios
RUN npm install react-pdf
RUN npm install pdfjs-dist
RUN npm install @react-pdf-viewer/core @react-pdf-viewer/zoom




# Copy the rest of the application files
COPY . .

# Build the app for production
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

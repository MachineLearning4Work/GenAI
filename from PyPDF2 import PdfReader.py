from PyPDF2 import PdfReader

def read_pdf_to_dict_and_text(pdf_path):
    """
    Reads a PDF file and returns:
    1. A dictionary with page numbers as keys and text as values
    2. A merged string of all text with '\n' between pages
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        tuple: (page_text_dict, merged_text)
    """
    # Dictionary to store page text
    page_text_dict = {}
    all_text_parts = []
    
    try:
        with open(pdf_path, 'rb') as file:
            # Initialize the PDF reader
            reader = PdfReader(file)
            
            # Iterate through each page
            for page_num, page in enumerate(reader.pages, start=1):
                # Extract text from the page
                page_text = page.extract_text()
                
                # Store in dictionary
                page_text_dict[page_num] = page_text
                
                # Add to list for merging
                all_text_parts.append(page_text)
        
        # Merge all text with newlines between pages
        merged_text = '\n'.join(all_text_parts)
        
        return page_text_dict, merged_text
    
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {pdf_path} was not found.")
    except Exception as e:
        raise Exception(f"An error occurred while reading the PDF: {str(e)}")

# Example usage
if __name__ == "__main__":
    pdf_path = "example.pdf"  # Replace with your PDF file path
    
    try:
        pages_dict, full_text = read_pdf_to_dict_and_text(pdf_path)
        
        # Print the dictionary content
        print("Page Text Dictionary:")
        for page_num, text in pages_dict.items():
            print(f"Page {page_num}: {text[:50]}...")  # Print first 50 chars
            
        # Print merged text preview
        print("\nMerged Text (first 200 characters):")
        print(full_text[:200] + "...")
        
        # Optionally save the merged text to a file
        with open("merged_text.txt", "w", encoding="utf-8") as output_file:
            output_file.write(full_text)
        print("\nMerged text saved to 'merged_text.txt'")
        
    except Exception as e:
        print(f"Error: {str(e)}")
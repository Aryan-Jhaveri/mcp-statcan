#\!/bin/bash

echo "Cleaning up resources directory..."

# Create backup of original resources
BACKUP_DIR="/Users/aryanjhaveri/Desktop/Projects/mcp-statcan/resources_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup at $BACKUP_DIR"
cp -r /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/src/resources $BACKUP_DIR

# Clean and copy only necessary files
echo "Replacing resources with clean version"
rm -rf /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/src/resources
mkdir -p /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/src/resources/metadata_demo

# Copy necessary files
cp -p cleaned_resources/*.json /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/src/resources/
cp -p cleaned_resources/metadata_demo/*.json /Users/aryanjhaveri/Desktop/Projects/mcp-statcan/src/resources/metadata_demo/

# Success message
echo "Resources cleanup complete."
echo "Original resources backed up to: $BACKUP_DIR"
echo "Removed unused resource files."


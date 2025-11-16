# Social Distribution Federation Setup

## Quick Start Guide

This document helps you connect your Social Distribution node with other nodes without needing to run complex shell commands.

## Step-by-Step Instructions

### 1. Node Configuration
1. Log in to your node as an admin user
2. Click on "Node Config" in the navigation menu
3. Enter your node's base URL (e.g., `https://your-app.herokuapp.com/`)
4. Create a service username and password for node-to-node communication
5. Save the configuration

### 2. Add Remote Node
1. Click on "Add Remote Node" in the navigation menu
2. Enter your connection partner's information:
   - Node name (e.g., "Partner Node")
   - Base URL (e.g., `https://their-app.herokuapp.com/`)
   - Service username 
   - Service password
3. Save the remote node configuration

### 3. Connect with Other Users
1. Navigate to the "Explore" page
2. Use the "Follow a Remote Author" form
3. Enter the full API URL of the user you want to follow:
   - Format: `https://their-node.herokuapp.com/api/authors/<uuid>/`
4. The follow request will be sent automatically

### 4. Approve Incoming Requests
1. Check your "Follow Requests" page regularly
2. Approve follow requests from remote users if you want mutual connection
3. Both parties need to follow each other for a complete connection

## Troubleshooting

- Make sure both nodes have each other listed as remote nodes
- Verify service account credentials are correct on both sides
- Ensure both parties have approved follow requests for two-way communication
- Check that base URLs match exactly on both sides

## Alternative: Command Line Setup

If you prefer command-line setup, you can use:

```bash
python setup_federation.py
```

This will guide you through the configuration process interactively.

## Management Command

For advanced users, there's also a Django management command:

```bash
python manage.py setup_node \
  --base-url="https://your-app.herokuapp.com/" \
  --service-username="service_user" \
  --service-password="service_pass" \
  --current-username="your_username"
```

## Need Help?

- Check the Federation Guide page in your node interface
- Ensure all configuration information matches exactly on both sides
- Contact your connection partner to verify their configuration
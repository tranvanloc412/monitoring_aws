# Setting Up a Python Virtual Environment and Installing Packages

## Step 1: Create a Virtual Environment

1. Open your terminal or command prompt.
2. Navigate to your project directory.
3. Run the following command to create a virtual environment:

   ```bash
   python3 -m venv venv
   ```

   This will create a directory named `venv` in your project folder.

## Step 2: Activate the Virtual Environment

  ```bash
  source .venv/bin/activate
  ```

Once activated, your terminal prompt should change to indicate that the virtual environment is active.

## Step 3: Install Packages from `requirements.txt`

1. Ensure your `requirements.txt` file is in the project directory.
2. Run the following command to install the packages:

   ```bash
   pip3 install -r requirements.txt
   ```

This will install all the packages listed in `requirements.txt` into your virtual environment.

## Step 4: Deactivate the Virtual Environment

When you're done working in the virtual environment, you can deactivate it by simply running:

```bash
deactivate
```

This will return your terminal to the global Python environment.

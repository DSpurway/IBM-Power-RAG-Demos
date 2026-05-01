# IBM Power RAG Demos - Complete Deployment Walkthrough

A step-by-step guide to deploying the RAG demo on IBM Power10 using OpenShift, with screenshots captured from a fresh deployment.

## Prerequisites

### For IBM Employees and Business Partners

This demo requires access to **IBM TechZone** to reserve an OpenShift on Power10 environment.

**TechZone Collection**: [Retrieval Augmented Generation (RAG) on IBM Power](https://techzone.ibm.com/collection/retrieval-augmented-generation-rag-on-power10)

![TechZone Collection](images/techzone-collection.png)

### What You'll Get

When you reserve the environment, you'll receive:
- OpenShift cluster running on IBM Power10
- Pre-configured with necessary storage
- Access credentials (username: `cecuser`)
- Console URL for web-based management

### Time Required

- **Environment Provisioning**: 1-2 hours (automated by TechZone)
- **Demo Deployment**: 30-45 minutes
- **Total Demo Duration**: ~2 hours from start to finish

---

## Step 1: Reserve Your Environment

1. **Access TechZone Collection**
   - Navigate to: https://techzone.ibm.com/collection/retrieval-augmented-generation-rag-on-power10
   - You'll see the collection overview page

![TechZone Collection Overview](images/techzone-collection-overview.png)

2. **Navigate to Environments**
   - Click on the "**Environments**" tab in the left sidebar menu
   - You'll see the available environment options

![TechZone Environments Tab](images/techzone-environments-tab.png)

3. **Select the Environment**
   - Look for the blue box labeled "**Environment - systems-2**"
   - Full name: "OpenShift on POWER10 - Bastion, 1 Master with NFS Storage"
   - Click on the "**systems-2 environment**" button at the bottom

![Systems-2 Environment](images/techzone-systems2-environment.png)

4. **Create Reservation**
   - Click "**Request an environment**" button
   - This opens the "Create a reservation" page

![Create Reservation Page](images/techzone-create-reservation.png)

5. **Select Reservation Type**
   - Under "Single environment reservation options"
   - Click the radio button for "**Request an environment**"

![Request Environment Option](images/techzone-request-environment.png)

6. **Fill in Reservation Details**

![Fill Out Reservation Form](images/techzone-fill-reservation.png)

   - **Name**: Leave as default "OpenShift on POWER10 - Bastion, 1 Master with NFS Storage"
   
   - **Purpose**: Select "**Demo**"
     - Description: "Deliver a client specific demonstration based on discovery with the client and aligns to the identified architecture"
   
   - **Sales Opportunity number**: Enter your IBM Sales Cloud opportunity number
     - Example format: `0063h00000MR2InAAD`
     - This links the reservation to your sales opportunity
     - Providing an opportunity number allows you to extend your reservation date
   
   - **Sales Opportunity product**: Auto-populated based on opportunity
     - Example: "Power10 L1024 Scale-out (30CM0)"
   
   - **Purpose description**: Enter details about what you're demonstrating:
     - Example: "RAG on Power10 demonstration"
     - Or: "Demonstrating Retrieval Augmented Generation with IBM Power for client evaluation"
     - Explain what you're doing, why you need it, and what you're trying to accomplish
   
   - **Preferred Geography**: Select "**North America**"
     - Currently, this is the only available option for this environment
     - The Power10 systems are hosted in North America data centers
   
   - **Notes**: (Optional) Any additional information about your reservation

![Reservation Dates and Options](images/techzone-dates-options.png)

7. **Set Reservation Dates**
   - **Start date and time**:
     - Default is current date/time
     - Can schedule for future if needed
     - Timezone shown (e.g., "Europe/London")
   
   - **End date and time**:
     - Default is 1 week (168 hours) from start
     - Adjust based on your demo needs
     - Maximum duration depends on purpose and opportunity
   
   - **Available duration**: Shows "Available for up to 1 week (168 hours)"

8. **Additional Options**
   - **Install an optional Let's Encrypt SSL certificate**: Select "False" (default)
     - Not needed for this demo
   
   - **OpenShift release**: Shows "**OpenShift 4.21 on POWER10 (Bastion with Single Master Node)**"
     - This field auto-populates after geography selection
     - **Important**: Wait for this to appear before proceeding
     - Moving too fast can cause the reservation to get stuck in a loop

![OpenShift Release Details](images/techzone-openshift-release.png)

9. **Check Availability**
   - Click "**Check Availability**" button
   - This verifies resources are available for your selected dates
   - You should see a success message popup:
     - "**Success**"
     - "Your current selected dates are available!"
     - Shows your start date and time with timezone
   - The word "**Validated**" appears below the button

![Check Availability Success](images/techzone-availability-success.png)

   > **Important Notes**:
   > - Purpose selection cannot be changed after creation
   > - Providing an IBM Sales Cloud opportunity number allows reservation extensions
   > - "Demo" purpose is ideal for client demonstrations
   > - **Wait for OpenShift release details to load** before clicking Check Availability
   > - Moving through the form too quickly can cause submission issues

10. **Accept Terms and Submit**
   - After seeing "Validated", scroll to the bottom of the page
   - Check the box: "☑ I agree to IBM Technology Zone's Terms & Conditions and End User Security Policies"
   - Click the "**Submit**" button
   - You'll receive a confirmation email immediately
   - The reservation will begin provisioning

![Submit Reservation](images/techzone-submit-reservation.png)

11. **Confirmation Email**
   - Immediately after submission, you'll receive an email:
     - **Subject**: "IBM Technology Zone - Status Update: Provisioning"
     - **Message**: "Your environment has started provisioning"
     - **Environment Name**: "OpenShift on POWER10 - Bastion 1 Master with NFS Storage"
     - **Collection Name**: "Retrieval Augmented Generation (RAG) on IBM Power"

![Provisioning Email](images/techzone-provisioning-email.png)

12. **Possible "Failed" Email (Don't Worry!)**
   - You may receive an email with:
     - **Subject**: "IBM Technology Zone - Status Update: Failed"
     - **Message**: "An action related to your environment has failed"
     - **Action**: "Resource provisioning"
   
   > **Important**: This is a known issue that gets automatically resolved!
   > - The TechZone team is automatically notified
   > - They will fix it without you needing to contact anyone
   > - **Do not cancel your reservation**
   > - **Do not create a new reservation**
   > - Just wait - the team is already working on it
   > - You'll receive a "Ready" email once they've resolved it

![Failed Email (Automatically Resolved)](images/techzone-failed-email.png)

13. **Wait for Provisioning**
   - The environment is being built automatically
   - Status: "Provisioning" (check in TechZone, not just email)
   - Typically takes 1-2 hours
   - Ignore the "Failed" email if provisioning continues
   - You'll receive another email when it's actually ready

14. **Ready Notification (Success!)**
   - After the team resolves any issues, you'll receive:
     - **Subject**: "IBM Technology Zone - Status Update: Ready"
     - **Message**: "Your environment is now provisioned"
     - **Environment Name**: "OpenShift on POWER10 - Bastion 1 Master with NFS Storage"
     - **Reservation ID**: Your unique reservation identifier (e.g., `69f3697164129889e73256bb`)
     - **Collection Name**: "Retrieval Augmented Generation (RAG) on IBM Power"
     - **Start Date**: When your reservation began (UTC time)
     - **End Date**: When your reservation expires (UTC time)
   
   - At the bottom of the email, you'll see:
     - "You can access environment details, including needed credentials, **here**."
     - The word "**here**" is a clickable link (highlighted in green box)

![Ready Email with Details](images/techzone-ready-email-full.png)

15. **Access Reservation Details Page**
   - Click the "**here**" link in the Ready email
   - This opens your reservation details page in TechZone
   
   The page shows:
   
   **Header Information**:
   - Environment name: "OpenShift on POWER10 - Bastion, 1 Master with NFS Storage"
   - **Date**: Start date (green) and End date (red)
   - **Expires in**: Countdown timer (e.g., "6 days, 4 hours, 20 minutes")

16. **Get OpenShift Credentials**
   - Scroll down on the reservation details page to find:
   
   **Access Information**:
   - VPN information (if needed for IBMers)
   
   **OpenShift Version**:
   - Shows version: 4.21
   
   **OpenShift Console URL**:
   - The web address to access your cluster
   - Example: `https://console-openshift-console.apps.p1265.cecc.ihost.com`
   - Click this link to open the OpenShift console
   
   **Bastion Name**:
   - SSH bastion host (for advanced users)
   - Example: `p1265-bastion.p1265.cecc.ihost.com`
   
   **Bastion Public IP Address**:
   - Public IP for SSH access
   - Example: `129.40.94.1`
   
   **User Account**:
   - Username: **`cecuser`**
   - This is your OpenShift login username
   
   **User Password**:
   - Password shown as dots (••••••••••••)
   - **Copy button** (📋) next to the password
   - Click the copy button to copy your password
   
   **User Information**:
   - Note: "The user account has been granted admin privileges and you should use the htpasswd login method to authenticate with it."
   
   **User Private SSH Key**:
   - Blue button to download SSH key (for advanced users)

![OpenShift Credentials Section](images/techzone-openshift-credentials.png)

   > **Action Required**: 
   > 1. Click the **copy button** (📋) next to the password to copy it
   > 2. Save the password somewhere safe (you'll need it in a moment)
   > 3. Note the username: `cecuser`
   > 4. Click the **OpenShift Console URL** link

---

## Step 2: Access OpenShift Console


### Security Certificate Warning (Expected!)

1. **Certificate Warning Appears**
   - When you first click the OpenShift Console URL, you'll see a security warning:
   - **"Your connection is not private"**
   - Warning message: "Attackers might be trying to steal your information from console-openshift-console.apps.p1265.cecc.ihost.com"
   - Error code: `NET::ERR_CERT_AUTHORITY_INVALID`
   
   > **This is normal!** The TechZone environment uses self-signed certificates for demo purposes. This is safe to proceed.

![Certificate Warning](images/ocp-certificate-warning.png)

2. **Bypass the Warning**
   - Click the "**Advanced**" button (bottom left)
   - This expands additional options and shows more details:
   
   **Additional message appears**:
   - "This server could not prove that it is **console-openshift-console.apps.p1265.cecc.ihost.com**"
   - "Its security certificate is not trusted by your computer's operating system"
   - "This may be caused by a misconfiguration or an attacker intercepting your connection"
   
   **Proceed link appears**:
   - At the bottom, you'll see a link: "**Proceed to console-openshift-console.apps.p1265.cecc.ihost.com (unsafe)**"
   - Despite the scary "(unsafe)" label, this is safe for TechZone demo environments

![Advanced Certificate Options](images/ocp-certificate-advanced.png)

3. **Proceed to OpenShift**
   - Click the "**Proceed to console-openshift-console.apps.p1265.cecc.ihost.com (unsafe)**" link
   - This will take you to the OpenShift login page
   
   > **Note**: You may need to accept this certificate warning each time you access the console. This is normal for demo environments with self-signed certificates.

Now that you have your credentials, let's log into OpenShift!

   - **Extend limit**: Number of extensions available
   - **Status: Ready** (Available for use)
   
   **Status Timeline**:
   - Shows progression: Requested → Pending Approval → Scheduled → Provisioning → **Ready** ✓
   

### Second Certificate Warning (OAuth)

4. **Another Certificate Warning**
   - After proceeding, you'll see **another** certificate warning
   - This time for: **oauth-openshift.apps.p1265.cecc.ihost.com**
   - Same message: "Your connection is not private"
   - Same error: `NET::ERR_CERT_AUTHORITY_INVALID`
   
   > **This is also normal!** OpenShift uses multiple services with self-signed certificates. You need to accept this one too.

![OAuth Certificate Warning](images/ocp-oauth-certificate-warning.png)

5. **Bypass Second Warning**
   - Click "**Advanced**" again (or "Hide advanced" if already expanded)
   - The expanded view shows:
     - "This server could not prove that it is **oauth-openshift.apps.p1265.cecc.ihost.com**"
     - "Its security certificate is not trusted by your computer's operating system"
     - "This may be caused by a misconfiguration or an attacker intercepting your connection"
   - At the bottom, click: "**Proceed to oauth-openshift.apps.p1265.cecc.ihost.com (unsafe)**"

![OAuth Certificate Advanced](images/ocp-oauth-certificate-advanced.png)

6. **Success!**
   - After bypassing the second certificate warning, you'll finally reach the OpenShift login page
   - No more certificate warnings (for this session)

   **Purpose Section**:

### OpenShift Login Page

7. **Select Authentication Method**
   - You'll see the OpenShift login page with "**Log in with**" at the top
   - Red Hat OpenShift logo on the right
   - Two authentication options are shown:
     - **kube:admin** (Kubernetes admin)
     - **htpasswd** (HTTP password authentication)
   
   > **Important**: Select **htpasswd** - this is the authentication method for your `cecuser` account.

![OpenShift Login Options](images/ocp-login-options.png)

8. **Click htpasswd**
   - Click the "**htpasswd**" button
   - This will take you to the username/password login form


### Enter Credentials

9. **Login Form**
   - You'll see the login form: "**Log in to your account**"
   - Red Hat OpenShift logo and "Welcome to Red Hat OpenShift" on the right
   - Two required fields:
     - **Username** *
     - **Password** *
   - Blue "**Log in**" button at the bottom

![OpenShift Login Form](images/ocp-login-form.png)

10. **Enter Your Credentials**
    - **Username**: Type `cecuser`
    - **Password**: Paste the password you copied earlier from the TechZone reservation page
      - The password will appear as dots (••••••••••••)
      - Make sure you copied it correctly from the TechZone page
    
    > **Tip**: If you didn't copy the password earlier, go back to your TechZone reservation details page and click the copy button next to the password.

11. **Log In**
    - Click the blue "**Log in**" button
    - OpenShift will authenticate your credentials
    - You'll be redirected to the OpenShift console dashboard

![Login with Credentials](images/ocp-login-with-credentials.png)


### Welcome Tour (Optional)

12. **OpenShift Console Dashboard**
    - After successful login, you'll see the OpenShift console
    - **Overview** page with cluster information
    - Left sidebar with navigation menu (Home, Workloads, Networking, Storage, etc.)
    - Top right shows your username: `cecuser`
    
13. **Welcome Tour Popup**
    - A popup appears: "**Welcome to the new OpenShift experience!**"
    - Illustration showing a person with a laptop
    - Message about the fresh modern look and improved navigation
    - Two options:
      - **Launch tour** (blue button)
      - **Skip tour** (text link)
    
    > **Recommendation**: Click "**Skip tour**" - we'll guide you through what you need for the demo.

![Welcome Tour Popup](images/ocp-welcome-tour.png)

14. **Skip the Tour**
    - Click "**Skip tour**"
    - The popup closes
    - You're now on the OpenShift Overview dashboard
    - You can see cluster details, activity, and getting started resources

![OpenShift Dashboard](images/ocp-dashboard-overview.png)

---

## Step 3: Create a Project

Now that you're logged into OpenShift, let's create a project (namespace) to hold all our demo components.

> **Note**: This walkthrough uses OpenShift 4.21.12 running on IBM Power10. The interface may look different from earlier versions.

### What is a Project?

In OpenShift, a **project** is a Kubernetes namespace with additional annotations. It provides:
- Isolation for your applications
- Resource quotas and limits
- Access control
- A logical grouping for related components

For this demo, we'll create a project called `llm-on-techzone` to hold:
- LLM service (TinyLlama + Granite models)
- OpenSearch vector database
- RAG backend API
- Carbon UI frontend

### Create Project Steps

15. **Working in Administrator Perspective**
    - You're currently in the **Administrator** perspective on the Overview dashboard
    - The left sidebar shows "⚙️ Core platform" at the top
    - This perspective provides full cluster management capabilities
    
    > **Note**: OpenShift 4.21.12 on Power10 makes Developer perspective difficult to access without cluster-level configuration changes. The Administrator perspective works perfectly fine for our demo deployment - we can create projects and deploy applications just as easily.
    
    > **What's the Difference?** Developer perspective provides a simplified, application-focused view. Administrator perspective shows the full cluster management interface. Both can deploy applications; Administrator just shows more options.

![Administrator Perspective Overview](images/ocp-administrator-overview.png)

16. **Navigate to Projects**
    - In the left sidebar, expand **"Home"** if it's not already expanded
    - Click on **"Projects"**
    - This will show you the list of projects (namespaces) in the cluster
    - You'll see any existing projects, or an empty list if this is a fresh cluster

![Navigate to Projects](images/ocp-navigate-projects.png)

17. **Projects List View**
    - You're now on the Projects page showing all existing projects
    - The page shows a table with columns: Name, Display name, Status, Requester, Memory, CPU, Created
    - You can see system projects like: default, kube-node-lease, kube-public, kube-system, openshift, etc.
    - These are OpenShift's built-in projects - we'll create our own
    - In the top-right corner, you'll see the blue **"Create Project"** button

![Projects List](images/ocp-projects-list.png)

18. **Click Create Project**
    - Click the blue **"Create Project"** button in the top-right corner
    - A dialog box will appear with a form to create a new project

![Create Project Button](images/ocp-create-project-button.png)

19. **Fill in Project Details**
    - A "Create Project" dialog appears with three fields:
      - **Name** * (required) - Enter: `llm-on-techzone`
      - **Display name** (optional) - Enter: `LLM on TechZone Demo`
      - **Description** (optional) - Enter: `RAG demo with Carbon UI, OpenSearch, and Granite LLM`
    - The Name field must be lowercase, no spaces (use hyphens)
    - Click the blue **"Create"** button at the bottom

![Create Project Dialog](images/ocp-create-project-dialog.png)

20. **Project Created Successfully**
    - The dialog closes
    - You're taken to the **Project Overview** page for `llm-on-techzone`
    - Breadcrumb at top shows: **Projects → Project details**
    - Project name displayed: **llm-on-techzone** with green "Active" status badge
    - Tabs available: **Overview**, Details, YAML, Workloads, RoleBindings
    
    **Getting started resources** section shows three cards:
    - **Create applications using samples** (Basic Quarkus, Basic Spring Boot)
    - **Build with guided documentation** (Get started with Quarkus, Get started with Spring)
    - **Explore new developer features** (AI Chatbot Helm chart, topology)
    
    **Details panel** (left) shows:
    - Name: llm-on-techzone
    - Requester: cecuser
    - Labels: kubernetes.io/metadata.name, pod-security labels
    
    **Status panel** (center) shows:
    - Green checkmark: Active
    
    **Utilization panel** shows:
    - CPU: Not available (no workloads yet)
    - Memory: Not available (no workloads yet)
    
    **Activity panel** (right) shows:
    - Ongoing: There are no ongoing activities
    - Recent events: There are no recent events

![Project Created - Overview Page](images/ocp-project-created.png)

---

### Deploy OpenSearch Using Import YAML

> **Note**: This deployment uses IBM's official ppc64le OpenSearch container image from the IBM Container Registry.
> Special thanks to Sumit Dubey for the [OpenSearch on Power article](https://community.ibm.com/community/user/blogs/sumit-dubey/2025/06/18/opensearch-an-alternative-to-elasticse) that helped identify this solution.

21. **Navigate to Import YAML**
    - Make sure you're in the `llm-on-techzone` project
    - Click the **"+"** button at the top of the OpenShift console
    - Select **"Import YAML"**

![Click Plus to Import YAML](images/ocp-click-plus-import-yaml.png)

22. **Copy the OpenSearch YAML**
    - Open the file: `Part3-RAG-Sales-Manual/opensearch-deployment/opensearch-deploy-simple.yaml`
    - Copy the entire contents of the file
    - Or use this YAML directly:

```yaml
# OpenSearch Deployment for IBM Power (ppc64le)
# Uses IBM-maintained ppc64le OpenSearch image from IBM Container Registry
# Source: https://community.ibm.com/community/user/blogs/priya-seth/2023/04/05/open-source-containers-for-power-in-icr

apiVersion: apps/v1
kind: Deployment
metadata:
  name: opensearch-service
  labels:
    app: opensearch-service
    app.kubernetes.io/part-of: ibm-power-rag-demos-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: opensearch-service
  template:
    metadata:
      labels:
        app: opensearch-service
    spec:
      containers:
      - name: opensearch
        image: icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0
        env:
        - name: discovery.type
          value: "single-node"
        - name: OPENSEARCH_JAVA_OPTS
          value: "-Xms512m -Xmx512m"
        - name: DISABLE_SECURITY_PLUGIN
          value: "true"
        ports:
        - containerPort: 9200
          name: http
        - containerPort: 9300
          name: transport
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1"
        volumeMounts:
        - name: opensearch-data
          mountPath: /usr/share/opensearch/data
      volumes:
      - name: opensearch-data
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: opensearch-service
  labels:
    app: opensearch-service
    app.kubernetes.io/part-of: ibm-power-rag-demos-app
spec:
  selector:
    app: opensearch-service
  ports:
  - name: http
    port: 9200
    targetPort: 9200
  - name: transport
    port: 9300
    targetPort: 9300
  type: ClusterIP
```

![Copy OpenSearch YAML](images/ocp-opensearch-copy-yaml.png)

23. **Paste YAML into Editor**
    - In the Import YAML dialog, you'll see a text editor
    - Paste the copied YAML content
    - The editor will validate the YAML syntax
    - You should see no errors (green checkmark or no warnings)

![Paste YAML](images/ocp-opensearch-paste-yaml.png)

24. **Review the Configuration**
    - The YAML creates two resources:
      - **Deployment**: `opensearch-service` (the OpenSearch pod)
      - **Service**: `opensearch-service` (internal network access)
    - Key settings:
      - **Image**: `icr.io/ppc64le-oss/opensearch-ppc64le:3.3.0` (IBM ppc64le build)
      - **Single-node mode**: No cluster setup needed
      - **Security disabled**: Simplified for demo
      - **Resources**: 1Gi-2Gi memory, 500m-1 CPU
      - **No route**: Not exposed externally (security best practice)

![Review YAML](images/ocp-opensearch-review-yaml.png)

25. **Create the Resources**
    - Click the blue **"Create"** button at the bottom
    - OpenShift will create both the Deployment and Service
    - You'll see a success message

![Create from YAML](images/ocp-opensearch-create-yaml.png)

26. **View in Topology**
    - After creation, click **"Topology"** in the left sidebar
    - You should see the `opensearch-service` deployment
    - The pod will start automatically
    - Status will show as a blue ring (starting) then green checkmark (running)

![Topology View](images/ocp-opensearch-topology.png)

27. **Monitor Pod Startup**
    - Click on the `opensearch-service` deployment in Topology
    - In the side panel, click on the **Pod** name
    - Or go to **Workloads** → **Pods** and find `opensearch-service-xxxxx-xxxxx`
    - Status progression:
      - `Pending` → `ContainerCreating` → `Running`
    - **Startup time**: 30-60 seconds (no build needed - uses pre-built image!)

![Pod Starting](images/ocp-opensearch-pod-starting.png)

28. **View Pod Logs**
    - Click on the running pod
    - Click the **Logs** tab
    - Watch for OpenSearch startup messages:
      ```
      Disabling OpenSearch Security Plugin
      Enabling execution of performance-analyzer-agent-cli
      [INFO ][o.o.n.Node] [opensearch-node1] initializing...
      [INFO ][o.o.n.Node] [opensearch-node1] initialized
      [INFO ][o.o.n.Node] [opensearch-node1] starting...
      [INFO ][o.o.n.Node] [opensearch-node1] started
      ```
    - When you see "started", OpenSearch is ready!

![OpenSearch Started](images/ocp-opensearch-logs-started.png)

29. **Verify Service Creation**
    - Navigate to **Networking** → **Services**
    - Find `opensearch-service` in the list
    - Verify details:
      - **Type**: ClusterIP
      - **Port**: 9200 → 9200 (TCP)
      - **Port**: 9300 → 9300 (TCP)
      - **Target Port**: 9200, 9300
    - This service allows internal cluster access to OpenSearch

![OpenSearch Service](images/ocp-opensearch-service-created.png)

30. **Test OpenSearch Health**
    - Click on the `opensearch-service` pod in **Workloads** → **Pods**
    - Click the **Terminal** tab
    - Run this command:
      ```bash
      curl http://localhost:9200/_cluster/health
      ```
    - Expected response:
      ```json
      {
        "cluster_name": "opensearch-cluster",
        "status": "green",
        "number_of_nodes": 1,
        "number_of_data_nodes": 1
      }
      ```
    - **Status "green"** means OpenSearch is healthy and ready!

![Test OpenSearch Health](images/ocp-opensearch-health-test.png)

### Configuration Summary

**OpenSearch Deployment Details:**
- **Name**: opensearch-service
- **Service**: opensearch-service (ClusterIP)
- **Port**: 9200
- **Version**: 2.11.0
- **Architecture**: ppc64le (IBM Power10)
- **Security**: Disabled (simplified for demo)
- **Discovery**: Single-node mode
- **Resources**: 1Gi-2Gi RAM, 500m-1 CPU

**Environment Variables for RAG Backend:**
```bash
OPENSEARCH_HOST=opensearch-service
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin  # Not used when security disabled
OPENSEARCH_PASSWORD=admin  # Not used when security disabled
OPENSEARCH_USE_SSL=false
```

These environment variables are already configured in the RAG backend Dockerfile, so no manual configuration needed!

### Troubleshooting

**Build Fails?**
- Check build logs: **Builds** → `opensearch-service` → **Logs**
- Common issues:
  - Network timeout downloading tarball: Retry the build
  - Insufficient build resources: Check cluster capacity
  - Wrong context directory: Verify `/Part3-RAG-Sales-Manual/opensearch-deployment`

**Pod Won't Start?**
- Check pod logs: **Workloads** → **Pods** → click pod → **Logs**
- Common issues:
  - OOMKilled: Increase memory limits to 2Gi-4Gi
  - CrashLoopBackOff: Check logs for Java errors
  - ImagePullBackOff: Build may have failed, check build status

**Can't Connect to OpenSearch?**
- Verify service exists: **Networking** → **Services** → `opensearch-service`
- Verify pod is running: **Workloads** → **Pods** → status should be "Running"
- Test from terminal: Use curl command in step 35
- Check port: Should be 9200

### What's Next?

With OpenSearch deployed and verified, we can now deploy the LLM services that will generate responses for our RAG demo.

---


## Step 4: Deploy OpenSearch

OpenSearch is the vector database that stores document embeddings and enables semantic search for our RAG demo. We'll deploy a single-node OpenSearch cluster suitable for demonstration purposes.

### What is OpenSearch?

OpenSearch is an open-source search and analytics engine that provides:
- **Vector Search**: k-NN (k-nearest neighbors) for semantic similarity
- **Full-Text Search**: BM25 keyword matching
- **Hybrid Search**: Combines vector and keyword search for best results
- **Scalability**: Production-ready distributed architecture

For our RAG demo, OpenSearch stores:
- Document chunks (text segments from PDFs)
- Vector embeddings (384-dimensional vectors from all-MiniLM-L6-v2 model)
- Metadata (source document, page numbers, etc.)

### Prerequisites

- ✅ Project `llm-on-techzone` created (Step 3)
- ✅ Administrator perspective access
- ✅ Sufficient cluster resources (2GB RAM, 1 CPU core minimum)

### Deployment Steps

![Navigate to OperatorHub](images/ocp-navigate-operatorhub.png)

22. **Search for OpenSearch**
    - In the search box at the top, type: `opensearch`
    - You should see the **OpenSearch Operator** tile
    - The operator is provided by the OpenSearch community
    - Click on the **OpenSearch Operator** tile

![Search OpenSearch Operator](images/ocp-search-opensearch-operator.png)

23. **Install the Operator**
    - A details panel opens on the right showing operator information
    - Review the operator details:
      - **Provider**: OpenSearch Project
      - **Capability Level**: Basic Install
      - **Repository**: GitHub opensearch-project
    - Click the blue **Install** button

![OpenSearch Operator Details](images/ocp-opensearch-operator-details.png)

24. **Configure Operator Installation**
    - The "Install Operator" page appears with configuration options
    - **Update channel**: Select `stable` (or latest available)
    - **Installation mode**: Choose "A specific namespace on the cluster"
    - **Installed Namespace**: Select `llm-on-techzone` (our project)
    - **Update approval**: Choose "Automatic" (recommended for demos)
    - Click **Install**

![Configure Operator Installation](images/ocp-configure-opensearch-install.png)

25. **Wait for Operator Installation**
    - The operator installation begins
    - Status shows "Installing"
    - This typically takes 1-2 minutes
    - Wait for status to change to "Succeeded"
    - You'll see a green checkmark when complete

![Operator Installing](images/ocp-opensearch-operator-installing.png)

26. **Verify Operator Installation**
    - Once installed, you'll see "Installed operator - ready for use"
    - Click **View Operator** to see the operator details
    - Or navigate to: **Operators** → **Installed Operators**
    - You should see **OpenSearch Operator** with status "Succeeded"

![Operator Installed](images/ocp-opensearch-operator-installed.png)

27. **Create OpenSearch Cluster**
    - From the Installed Operators page, click **OpenSearch Operator**
    - You'll see the operator details page
    - Under "Provided APIs", find **OpenSearchCluster**
    - Click **Create instance** under OpenSearchCluster

![Create OpenSearch Instance](images/ocp-create-opensearch-instance.png)

28. **Configure OpenSearch Cluster (YAML)**
    - The "Create OpenSearchCluster" page opens with a YAML editor
    - Replace the default YAML with this configuration:

```yaml
apiVersion: opensearch.opster.io/v1
kind: OpenSearchCluster
metadata:
  name: opensearch-cluster
  namespace: llm-on-techzone
spec:
  general:
    serviceName: opensearch-service
    version: 2.11.0
    httpPort: 9200
    vendor: opensearch
    pluginsList:
      - analysis-icu
      - analysis-kuromoji
      - analysis-nori
      - analysis-phonetic
      - analysis-smartcn
      - analysis-stempel
      - analysis-ukrainian
  dashboards:
    enable: false
  nodePools:
    - component: masters
      replicas: 1
      diskSize: 10Gi
      resources:
        requests:
          memory: 2Gi
          cpu: 1
        limits:
          memory: 4Gi
          cpu: 2
      roles:
        - master
        - data
  security:
    config:
      adminCredentialsSecret:
        name: opensearch-admin-credentials
      securityConfigSecret:
        name: opensearch-security-config
```

![OpenSearch Cluster YAML](images/ocp-opensearch-cluster-yaml.png)

29. **Create Admin Credentials Secret (First)**
    - Before creating the cluster, we need to create the admin credentials secret
    - Click the **"+"** (Import YAML) button in the top navigation
    - Paste this YAML:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: opensearch-admin-credentials
  namespace: llm-on-techzone
type: Opaque
stringData:
  username: admin
  password: admin
```

    - Click **Create**
    - This creates the admin credentials (username: admin, password: admin)

![Create Admin Credentials](images/ocp-create-opensearch-credentials.png)

30. **Create Security Config Secret**
    - Click the **"+"** button again
    - Paste this YAML:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: opensearch-security-config
  namespace: llm-on-techzone
type: Opaque
stringData:
  config.yml: |
    _meta:
      type: "config"
      config_version: 2
    config:
      dynamic:
        http:
          anonymous_auth_enabled: false
        authc:
          basic_internal_auth_domain:
            http_enabled: true
            transport_enabled: true
            order: 0
            http_authenticator:
              type: basic
              challenge: false
            authentication_backend:
              type: internal
```

    - Click **Create**

![Create Security Config](images/ocp-create-security-config.png)

31. **Now Create the OpenSearch Cluster**
    - Go back to **Operators** → **Installed Operators** → **OpenSearch Operator**
    - Click **Create instance** under OpenSearchCluster again
    - Paste the cluster YAML from step 28
    - Click **Create**
    - The OpenSearch cluster deployment begins

![Create Cluster](images/ocp-create-opensearch-cluster.png)

32. **Monitor Cluster Deployment**
    - Navigate to **Workloads** → **Pods**
    - You should see pods being created:
      - `opensearch-cluster-masters-0` - The OpenSearch node
    - Status will show "ContainerCreating" then "Running"
    - This takes 3-5 minutes (downloading image, starting OpenSearch)
    - Wait for the pod to show **Running** with **1/1** ready

![OpenSearch Pods](images/ocp-opensearch-pods.png)

33. **Verify OpenSearch Service**
    - Navigate to **Networking** → **Services**
    - You should see a service named `opensearch-service`
    - Type: ClusterIP
    - Port: 9200
    - This is the internal service the RAG backend will use

![OpenSearch Service](images/ocp-opensearch-service.png)

34. **Test OpenSearch Connection (Optional)**
    - To verify OpenSearch is working, we can test from a terminal pod
    - Navigate to **Workloads** → **Pods**
    - Click on the `opensearch-cluster-masters-0` pod
    - Click the **Terminal** tab
    - Run this command:

```bash
curl -u admin:admin -k https://localhost:9200
```

    - You should see JSON output with cluster information
    - Look for `"cluster_name" : "opensearch-cluster"`

![Test OpenSearch](images/ocp-test-opensearch.png)

### Configuration Summary

**OpenSearch Cluster Details:**
- **Name**: opensearch-cluster
- **Service**: opensearch-service
- **Port**: 9200
- **Username**: admin
- **Password**: admin
- **Version**: 2.11.0
- **Resources**: 2Gi RAM, 1 CPU (request), 4Gi RAM, 2 CPU (limit)
- **Storage**: 10Gi persistent volume

**Environment Variables for RAG Backend:**
```bash
OPENSEARCH_HOST=opensearch-service
OPENSEARCH_PORT=9200
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin
```

### Troubleshooting

**Pod not starting?**
- Check pod logs: **Workloads** → **Pods** → click pod → **Logs** tab
- Common issues:
  - Insufficient resources: Increase cluster capacity or reduce resource requests
  - Image pull errors: Check network connectivity
  - PVC binding issues: Verify storage class availability

**Operator installation failed?**
- Check operator logs: **Operators** → **Installed Operators** → **OpenSearch Operator** → **Logs** tab
- Verify namespace permissions
- Try uninstalling and reinstalling the operator

**Can't connect to OpenSearch?**
- Verify service exists: **Networking** → **Services**
- Check pod is running: **Workloads** → **Pods**
- Test from terminal pod (step 34)
- Verify credentials secret was created correctly

### What's Next?

With OpenSearch deployed, we can now deploy the LLM services that will generate responses for our RAG demo.

---

## Step 5: Deploy TinyLlama LLM Service

Now we'll deploy the TinyLlama 1.1B language model. This lightweight model is perfect for demonstrating basic LLM capabilities and showing hallucinations (incorrect responses) when asked questions without RAG context.

### Why TinyLlama First?

- **Part 1 Demo**: Shows basic LLM queries and hallucinations (no RAG needed)
- **Lightweight**: Only 1.1B parameters, faster to download and deploy
- **Power-Compatible**: Uses llama.cpp which has excellent IBM Power support
- **No Dependencies**: Works standalone without OpenSearch

> **Note**: We'll deploy the more capable Granite 4.0 model later for Part 3 (RAG with technical documents).

---

### Step 5.1: Start Import from Git

1. **Click the "+" button** in the top navigation bar
   
   ![Plus Button Location](images/ocp-plus-button.png)

2. **Select "Import from Git"** from the dropdown menu

3. **Fill in the Git Repository URL**:
   ```
   https://github.com/DSpurway/IBM-Power-RAG-Demos
   ```

4. **Click "Show advanced Git options"** button

   ![Import from Git Form](images/tinyllama-import-git-form.png)

---

### Step 5.2: Configure Advanced Git Options

5. **Fill in Context Directory**:
   ```
   /Part3-RAG-Sales-Manual/llama-cpp-server
   ```
   
   > This tells OpenShift which subdirectory contains the Dockerfile

6. **Click "Edit Import Strategy"** link (blue text next to Dockerfile icon)

   ![Edit Import Strategy Button](images/tinyllama-edit-import-strategy-button.png)

7. **In the Import Strategy dialog**:
   - Ensure **"Dockerfile"** strategy is selected
   - **Dockerfile path**: Change to `Dockerfile.tinyllama`
   - You should see a green checkmark with "Validated"
   - The message should say: "The Dockerfile at Dockerfile.tinyllama is recommended"

   ![Import Strategy Dialog](images/tinyllama-import-strategy-dialog.png)

   > **Why Dockerfile.tinyllama?** The directory contains two Dockerfiles:
   > - `Dockerfile` - For Granite 4.0 (larger model, used in Part 3)
   > - `Dockerfile.tinyllama` - For TinyLlama 1.1B (what we need now)

8. **Close the Import Strategy dialog** (click outside or press Escape)

---

### Step 5.3: Configure Application Settings

9. **Scroll down** to see the remaining form fields

10. **Application name**:
    - Leave as `ibm-power-rag-demos-app` (or change if you prefer)
    - This groups related services together in the topology view

11. **Name**: Change to `tinyllama-service`
    
    > **Critical**: This must be `tinyllama-service` because the RAG backend expects this service name:
    > ```python
    > TINYLLAMA_HOST = os.environ.get('TINYLLAMA_HOST', 'tinyllama-service')
    > ```

   ![Application and Name Settings](images/tinyllama-application-name-settings.png)

12. **Scroll down to Advanced options section**

13. **Target port**: Leave as `8080`
    - This is the port llama.cpp server listens on (from Dockerfile `EXPOSE 8080`)

14. **Create a route**:
    - ☐ **UNCHECK this option**
    - TinyLlama will only be accessed internally by the RAG backend
    - No external route needed for production architecture
    
    > **Architecture**: Browser → Carbon UI → RAG Backend → `tinyllama-service:8080` (internal)

   ![Advanced Options - Route Disabled](images/tinyllama-advanced-options-no-route.png)

15. **Review your configuration**:
    - Git Repo: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
    - Context Dir: `/Part3-RAG-Sales-Manual/llama-cpp-server`
    - Dockerfile: `Dockerfile.tinyllama`
    - Name: `tinyllama-service`
    - Target port: 8080
    - Route: ☐ Disabled (internal access only)

---

### Step 5.4: Create the Deployment

15. **Click the "Create" button** at the bottom of the form

16. **Wait for redirect** to the Topology view
    - You should see a new deployment icon for `tinyllama-service`
    - The outer ring will show build progress

---

### Step 5.5: Monitor the Build

17. **Click on the tinyllama-service icon** in the Topology view

18. **View Build Logs**:
    - In the right panel, click the **"View logs"** link under the build section
    - Or go to **Builds** → **Builds** → **tinyllama-service-1** → **Logs** tab

19. **What to expect in the logs**:
    ```
    Step 1/8 : FROM ghcr.io/ggerganov/llama.cpp:server
    Step 2/8 : RUN apt-get update && apt-get install -y curl
    Step 3/8 : WORKDIR /models
    Step 4/8 : RUN curl -L -o tinyllama-1.1b-chat-v1.0.Q8_0.gguf \
        https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q8_0.gguf
    ```
    
    > **Note**: Downloading the model from HuggingFace takes 5-10 minutes depending on network speed

20. **Build completion**:
    - Look for: `Successfully tagged ...`
    - Look for: `Push successful`
    - Build status will change from "Running" to "Complete"

---

### Step 5.6: Verify Deployment

21. **Check Pod Status**:
    - Go to **Workloads** → **Pods**
    - Find `tinyllama-service-xxxxx-xxxxx` pod
    - Status should be "Running"
    - Ready: 1/1

22. **View Pod Logs**:
    - Click on the pod name
    - Click **Logs** tab
    - Look for llama.cpp server startup messages:
    ```
    llama server listening at http://0.0.0.0:8080
    ```

23. **Get the Route URL**:
    - Go to **Networking** → **Routes**
    - Find `tinyllama-service` route
    - Copy the **Location** URL (e.g., `http://tinyllama-service-llm-on-techzone.apps...`)

---

### Step 5.7: Test the LLM Endpoint

24. **Test the health endpoint**:
    ```bash
    curl http://tinyllama-service-llm-on-techzone.apps.YOUR-CLUSTER/health
    ```
    
    Expected response:
    ```json
    {
      "status": "ok"
    }
    ```

25. **Test a simple completion**:
    ```bash
    curl -X POST http://tinyllama-service-llm-on-techzone.apps.YOUR-CLUSTER/v1/completions \
      -H "Content-Type: application/json" \
      -d '{
        "prompt": "What is the capital of France?",
        "max_tokens": 50,
        "temperature": 0.7
      }'
    ```
    
    Expected response:
    ```json
    {
      "choices": [
        {
          "text": " Paris is the capital of France..."
        }
      ]
    }
    ```

---

### Troubleshooting TinyLlama Deployment

**Build fails with "no image found in manifest list for architecture 'ppc64le'"?**
- This means you're using an x86_64-only image
- Verify you selected `Dockerfile.tinyllama` (not `Dockerfile`)
- The llama.cpp base image supports Power architecture

**Build takes too long (>15 minutes)?**
- The model download from HuggingFace can be slow
- Check build logs to see if download is progressing
- Network issues may require retry

**Pod crashes with OOMKilled?**
- TinyLlama needs at least 2Gi memory
- Increase memory limits in deployment configuration
- Check cluster has available resources

**Can't access the route?**
- Verify route was created: **Networking** → **Routes**
- Check pod is running: **Workloads** → **Pods**
- Test from inside cluster first using service name

**llama.cpp server not starting?**
- Check pod logs for error messages
- Verify model file was downloaded correctly
- Ensure port 8080 is not blocked

---

### What's Next?

With TinyLlama deployed, we can now:
- **Part 1 Demo**: Test basic LLM queries (shows hallucinations without RAG)
- **Deploy RAG Backend**: Connect TinyLlama to the RAG system
- **Deploy Carbon UI**: Create the web interface

---

## Topology View: All Services Building

After deploying all three services, your OpenShift Topology view should look like this:

![All Services Building](images/topology-all-services-building.png)

### What You're Seeing:

**Three Deployments:**
1. **tinyll...ervice** (TinyLlama LLM)
   - Blue ring = Build in progress
   - Green checkmark = Git source connected
   - Internal service (no route icon)

2. **carbon-rag-ui** (Frontend)
   - Blue ring = Build in progress  
   - Sync icon = Building
   - External route icon (arrow) = Public access enabled

3. **rag-backend** (API Service)
   - Blue ring = Build in progress
   - Sync icon = Building
   - Internal service (no route icon)

**Application Grouping:**
- All three services grouped under `ibm-power-rag-demos-app` (green label)
- This makes it easy to manage related services together

### Build Status Indicators:

**Blue Ring (Building):**
- Outer ring shows build progress
- Will turn dark blue when deployed

**Icons:**
- 🔄 Sync icon = Currently building
- ✅ Green checkmark = Source connected
- 🔗 Chain link = Service connection
- 🌐 Arrow icon = External route available

### Monitoring Builds:


---

## Step 7: Deploy Carbon UI Frontend

The Carbon UI is the user-facing web application built with:
- **Next.js 14** - React framework with server-side rendering
- **IBM Carbon Design System** - Professional IBM UI components
- **Three demo parts**:
  - Home page with demo selection
  - Harry Potter RAG (Part 2)
  - IBM Power Sales Manual RAG (Part 3)

### Key Difference: This Needs External Access!

Unlike TinyLlama and RAG Backend (internal services), the Carbon UI:
- ✅ **NEEDS a route** - Users access it from their browser
- ✅ **External URL** - Will be accessible outside the cluster
- 🔒 **Proxies backend calls** - Next.js API routes handle backend communication

---

### Step 7.1: Start Import from Git

1. **Click "+" button** → **"Import from Git"**

2. **Git Repo URL**: 
   ```
   https://github.com/DSpurway/IBM-Power-RAG-Demos
   ```

3. **Click "Show advanced Git options"**

4. **Context dir**: 
   ```
   /Part3-RAG-Sales-Manual/carbon-rag-ui
   ```

---

### Step 7.2: Verify Dockerfile Detection

5. **OpenShift auto-detects Dockerfile**:
   - "Multiple import strategies detected"
   - "The Dockerfile at Dockerfile is recommended" ✅
   - Default Dockerfile is correct

---

### Step 7.3: Configure Application Settings

6. **Application**: Select `ibm-power-rag-demos-app`
   - Groups with TinyLlama and RAG Backend

7. **Name**: Enter `carbon-rag-ui`
   
   > This will be the service name and part of the route URL

---

### Step 7.4: Configure Advanced Options

8. **Target port**: `3000`
   - Next.js default port

9. **Create a route**: ✅ **CHECK this option**
   - **IMPORTANT**: Unlike the backend services, we NEED external access
   - This creates a public URL for browser access

10. **Review configuration**:
    - Git Repo: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
    - Context Dir: `/Part3-RAG-Sales-Manual/carbon-rag-ui`
    - Dockerfile: `Dockerfile` (default)
    - Application: `ibm-power-rag-demos-app`
    - Name: `carbon-rag-ui`
    - Target port: 3000
    - Route: ✅ **Enabled** (external access)

---

### Step 7.5: Create and Monitor

11. **Click "Create"**

12. **Monitor build** (takes 5-10 minutes):
    - Installing Node.js dependencies
    - Building Next.js application
    - Creating production bundle

13. **Build logs will show**:
    ```
    npm install
    npm run build
    Creating an optimized production build...
    Route (app)                              Size
    ┌ ○ /                                    142 kB
    ├ ○ /api/rag/generate                    0 B
    └ ○ /harry-potter                        145 kB
    ```

---

### Step 7.6: Access the Carbon UI

14. **Wait for deployment to complete**:
    - Pod status: "Running"
    - Ready: 1/1
    - Blue ring turns dark blue in Topology view

15. **Get the Route URL**:
    - **Option A**: Click the arrow icon on the deployment in Topology view
    - **Option B**: Go to **Networking** → **Routes** → Find `carbon-rag-ui` → Copy Location URL

16. **Handle SSL Certificate Warning (Part 1)**:
    
    When you click the route, you'll see a browser security warning:
    
    ![SSL Certificate Warning - Initial](images/carbon-ui-ssl-warning-1.png)
    
    **Initial Warning Message**:
    ```
    Your connection is not private
    
    Attackers might be trying to steal your information from
    carbon-rag-ui-llm-on-techzone.apps.p1265.cecc.ihost.com
    
    NET::ERR_CERT_AUTHORITY_INVALID
    ```
    
    **Why This Happens**:
    - OpenShift routes use self-signed SSL certificates
    - Your browser doesn't recognize the certificate authority
    - This is normal for development/demo environments
    
    **First Step**: Click **"Advanced"** button (or "Hide advanced" if already expanded)

17. **Handle SSL Certificate Warning (Part 2)**:
    
    After clicking "Advanced", you'll see more details:
    
    ![SSL Certificate Warning - Advanced](images/carbon-ui-ssl-warning-2.png)
    
    **Expanded Warning**:
    ```
    This server could not prove that it is carbon-rag-ui-llm-on-
    techzone.apps.p1265.cecc.ihost.com; its security certificate
    is not trusted by your computer's operating system. This may
    be caused by a misconfiguration or an attacker intercepting
    your connection.
    
    Proceed to carbon-rag-ui-llm-on-techzone.apps.p1265.cecc.ihost.com (unsafe)
    ```
    
    **How to Proceed**:
    - Click the link: **"Proceed to carbon-rag-ui-llm-on-techzone... (unsafe)"**
    - Despite the "unsafe" warning, this is safe in a demo environment
    - The certificate is self-signed by OpenShift, not an attacker
    
    > **Note**: This is the same certificate warning you saw when accessing the OpenShift console. It's safe to proceed in a demo environment. The "unsafe" label is the browser's standard warning for any untrusted certificate.

17. **You should now see the Carbon UI home page!**

    ![Carbon UI Home Page](images/carbon-ui-home-page.png)

---

### Step 7.7: Verify the Application

18. **Check the home page displays**:
    - IBM branding and Carbon Design System styling
    - Three demo cards:
      - Part 1: Basic LLM Queries
      - Part 2: Harry Potter RAG
      - Part 3: IBM Power Sales Manual RAG
    - Navigation menu
    - Footer with links

19. **Check browser console** (F12 → Console tab):
    - Should be no errors
    - May see some info messages about Next.js

20. **Note the URL format**:
    ```
    http://carbon-rag-ui-llm-on-techzone.apps.p1265.cecc.ihost.com
    ```
    
    Components:
    - `carbon-rag-ui` - Service name
    - `llm-on-techzone` - Project name
    - `apps.p1265.cecc.ihost.com` - Cluster domain

---

### Troubleshooting Carbon UI

**Build fails with npm errors?**
- Check build logs for specific package failures
- Node.js version compatibility issues
- Try rebuilding: **Builds** → **Builds** → **Start Build**


---

## Step 8: Test Part 1 Demo (Basic LLM - No RAG)

Now that all services are running, let's test the Part 1 demo to see TinyLlama in action!

### What Part 1 Demonstrates

**Purpose**: Show how LLMs can "hallucinate" (generate plausible but incorrect information) when they don't have access to relevant context.

**Key Learning**: This demonstrates why RAG (Retrieval Augmented Generation) is important - by providing relevant context from documents, we can dramatically improve accuracy.

---

### Step 8.1: Navigate to Part 1

18. **You should already be on the Harry Potter RAG page**
    
    If not, click **"Harry Potter RAG"** in the top navigation

19. **Click the "Part 1: Simple Q&A" tab**

    ![Part 1 Interface](images/part1-simple-qa-interface.png)

    **Interface Elements**:
    - **Title**: "Part 1: Simple Q&A with TinyLlama"
    - **Description**: Explains the demo purpose
    - **Question input**: Large text area
    - **Ask Question button**: Sends query to TinyLlama
    - **Tabs**: Part 1, About RAG, Part 2, Credits

---

### Step 8.2: Ask a Question

20. **Type a question in the text area**

    Good test questions:
    ```
    Who is Warwick Davis?
    ```
    ```
    What house is Harry Potter in at Hogwarts?
    ```
    ```
    Who is the headmaster of Hogwarts?
    ```

21. **Click "Ask Question" button** (or press Enter)

---

### Step 8.3: Watch the Streaming Response

22. **Observe the response streaming in real-time**

    ![Part 1 Streaming Response](images/part1-streaming-response.png)

    **What You'll See**:
    - Response appears word-by-word (streaming)
    - TinyLlama generates text based on its training
    - May include accurate information
    - May include hallucinations (incorrect details)
    - Response completes in 5-30 seconds

    **Example Response** (may vary):
    ```
    Warwick Davis is a British actor known for his roles in 
    various films and television shows. He is perhaps best 
    known for playing Professor Flitwick in the Harry Potter 
    film series...
    ```

---

### Step 8.4: Evaluate the Response

23. **Check for hallucinations**

    **Common Issues with TinyLlama (No RAG)**:
    - ❌ May confuse characters or actors
    - ❌ May invent plausible-sounding but false details
    - ❌ May mix information from different sources
    - ✅ May get some basic facts correct
    - ✅ Response sounds confident even when wrong

24. **Try multiple questions** to see different behaviors

    **Questions that often show hallucinations**:
    - Specific plot details
    - Character relationships
    - Exact quotes or scenes
    - Technical specifications
    - Dates and timelines

---

### Step 8.5: Understanding the Results

**Why Hallucinations Happen**:
- TinyLlama is a small model (1.1B parameters)
- Trained on general internet text, not Harry Potter specifically
- No access to actual Harry Potter books
- Generates text based on patterns, not facts
- Tries to sound confident even when uncertain

**This is Normal!** 
- All LLMs can hallucinate
- Larger models (like Granite) hallucinate less but still do
- This is exactly why we need RAG!

---

### Step 8.6: Compare with RAG (Preview)

25. **Note your question and response**

26. **Later, in Part 2**, you'll ask the same question with RAG enabled:
    - System will search Harry Potter documents
    - Find relevant passages
    - Provide them as context to the LLM
    - Get much more accurate responses

**The Difference**:
```
Part 1 (No RAG):  "Warwick Davis played Professor Flitwick..."
                  ❌ May include incorrect details

Part 2 (With RAG): "According to the text, Warwick Davis 
                   played Professor Flitwick and Griphook..."
                  ✅ Cites actual source material
```

---

### Troubleshooting Part 1

**No response appears?**
- Check browser console (F12) for errors
- Verify backend is running: `oc get pods | grep rag-backend`
- Verify TinyLlama is running: `oc get pods | grep tinyllama`
- Check backend logs: `oc logs deployment/rag-backend`

**Response is very slow?**
- TinyLlama may be under load
- Check pod resources: `oc describe pod <tinyllama-pod-name>`
- Response should complete within 30 seconds

**"No response received" appears?**
- This can happen intermittently when TinyLlama is busy
- **Solution**: Simply ask the question again
- The model may have been processing a previous request
- This is normal for a single-instance deployment
- If it persists, check pod logs

**Error message appears?**
- "Failed to connect to backend" - Backend pod may be down
- "Model not responding" - TinyLlama pod may be restarting
- Check pod status and logs

**Response seems cut off?**
- This is normal - TinyLlama has token limits
- Longer responses may be truncated
- Try shorter, more specific questions

---

### What's Working Now

**Complete Part 1 Flow**:
```
1. User types question in browser
2. Carbon UI sends to Next.js API route
3. API route forwards to RAG backend (internal)
4. Backend sends prompt to TinyLlama (internal)
5. TinyLlama generates response (streaming)
6. Response streams back through chain
7. User sees real-time text generation
```

**Architecture Verified**:
- ✅ Browser → Carbon UI (external route working)
- ✅ Carbon UI → RAG Backend (internal service working)
- ✅ RAG Backend → TinyLlama (internal service working)
- ✅ Streaming responses (WebSocket/SSE working)
- ✅ Carbon Design System (UI rendering correctly)

---

### Next Steps

**Part 1 Complete!** You've successfully:
- ✅ Deployed all three services
- ✅ Accessed the Carbon UI
- ✅ Tested basic LLM queries
- ✅ Observed hallucinations

**To Enable Parts 2 & 3**:
1. Deploy OpenSearch (vector database)
2. Load Harry Potter documents (Part 2)
3. Load IBM Power sales manuals (Part 3)
4. Test RAG-enhanced responses
5. Compare accuracy with Part 1

---

**Pod crashes or won't start?**
- Check pod logs: **Workloads** → **Pods** → click pod → **Logs**
- Look for Next.js startup errors
- Verify port 3000 is not conflicting

**Can't access the route?**
- Verify route was created: **Networking** → **Routes**
- Check pod is running: **Workloads** → **Pods**
- Try the route URL directly (copy/paste into browser)

**Page loads but shows errors?**
- Check browser console (F12)
- Verify backend service is running: `oc get pods | grep rag-backend`
- Test backend connectivity from UI pod

**SSL certificate keeps blocking?**
- This is normal for self-signed certificates
- You must click "Advanced" → "Proceed" each time
- Production deployments should use proper SSL certificates

---

### What's Working Now!

With all three services deployed and running:

```
Browser (External)
    ↓ (HTTPS with self-signed cert)
carbon-rag-ui:3000 (route: http://carbon-rag-ui-...)
    ↓ (Next.js API routes - internal)
rag-backend:8080 (internal service)
    ↓ (internal)
tinyllama-service:8080 (internal service)
```

**Part 1 Demo is Ready!**
- ✅ TinyLlama LLM running
- ✅ RAG Backend running
- ✅ Carbon UI accessible from browser
- ✅ Can test basic LLM queries

**Not Yet Working:**
- ❌ Part 2 & 3 - Need OpenSearch for RAG
- ❌ Document loading - Need OpenSearch
- ❌ Vector search - Need OpenSearch

---

**Click any deployment** to see:
- Build logs (right panel)
- Pod status
- Resource details
- Events

**Expected Build Times:**
- TinyLlama: 5-10 minutes (model download)
- RAG Backend: 10-15 minutes (PyTorch installation)
- Carbon UI: 5-10 minutes (Next.js build)

---


---

## Step 6: Deploy RAG Backend Service

The RAG backend is the core service that:
- Connects to OpenSearch for vector storage (Part 2)
- Interfaces with LLM services (TinyLlama, Granite)
- Provides REST API for document loading and querying
- Handles PDF processing and web scraping
- Manages embeddings and semantic search

### Why Deploy Backend Before OpenSearch?

For **Part 1** (basic LLM demo), the backend can work without OpenSearch:
- Direct LLM queries don't need vector storage
- Demonstrates LLM hallucinations without RAG
- Backend gracefully handles missing OpenSearch connection

We'll add OpenSearch in Part 2 to enable full RAG capabilities.

---

### Step 6.1: Start Import from Git

1. **Click the "+" button** in the top navigation bar

2. **Select "Import from Git"**

3. **Fill in the Git Repository URL**:
   ```
   https://github.com/DSpurway/IBM-Power-RAG-Demos
   ```

4. **Click "Show advanced Git options"**

5. **Fill in Context Directory**:
   ```
   /Part3-RAG-Sales-Manual/rag-backend
   ```

---

### Step 6.2: Verify Dockerfile Detection

6. **OpenShift auto-detects the Dockerfile**:
   - You'll see: "Multiple import strategies detected"
   - Message: "The Dockerfile at Dockerfile is recommended"
   - This is correct - we want the default `Dockerfile`

   ![RAG Backend Import Strategy](images/rag-backend-import-strategy.png)

7. **No need to click "Edit Import Strategy"** - the default Dockerfile is correct

---

### Step 6.3: Configure Application Settings

8. **Application**: Select `ibm-power-rag-demos-app`
   - This groups the backend with TinyLlama in the topology view

9. **Name**: Enter `rag-backend`
   
   > **Critical**: This must be `rag-backend` because the Carbon UI expects this service name:
   > ```javascript
   > const RAG_BACKEND_URL = process.env.RAG_BACKEND_URL || 'http://rag-backend:8080';
   > ```

   ![RAG Backend Name Configuration](images/rag-backend-name-config.png)

---

### Step 6.4: Configure Advanced Options

10. **Scroll down** to Advanced options section

11. **Target port**: Enter `8080`
    - This is the port the Flask/Gunicorn server listens on

12. **Create a route**: ☐ **UNCHECK this option**
    - Backend is accessed internally by Carbon UI
    - No external route needed
    - Architecture: Browser → Carbon UI → `rag-backend:8080` (internal)

13. **Review your configuration**:
    - Git Repo: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
    - Context Dir: `/Part3-RAG-Sales-Manual/rag-backend`
    - Dockerfile: `Dockerfile` (default)
    - Application: `ibm-power-rag-demos-app`
    - Name: `rag-backend`
    - Target port: 8080
    - Route: ☐ Disabled

---

### Step 6.5: Create the Deployment

14. **Click the "Create" button**

15. **Wait for redirect** to the Topology view
    - You should see both `tinyllama-service` and `rag-backend` deployments
    - Both grouped under `ibm-power-rag-demos-app`

---

### Step 6.6: Monitor the Build

16. **Click on the rag-backend icon** in the Topology view

17. **View Build Logs**:
    - Click **"View logs"** link in the right panel
    - Or go to **Builds** → **Builds** → **rag-backend-1** → **Logs** tab

18. **What to expect in the logs**:
    ```
    Step 1/X : FROM registry.access.redhat.com/ubi9/python-312:latest AS builder
    Step 2/X : RUN dnf install -y gcc gcc-c++ git make...
    Step 3/X : COPY requirements.txt .
    Step 4/X : RUN pip install --no-cache-dir --prefer-binary torch...
    ```
    
    > **Note**: Installing PyTorch and ML dependencies takes 10-15 minutes
    > The build uses IBM Power-optimized wheels for better performance

19. **Build completion**:
    - Look for: `Successfully tagged ...`
    - Look for: `Push successful`
    - Build status changes to "Complete"

---

### Step 6.7: Verify Deployment

20. **Check Pod Status**:
    - Go to **Workloads** → **Pods**
    - Find `rag-backend-xxxxx-xxxxx` pod
    - Status should be "Running"
    - Ready: 1/1

21. **View Pod Logs**:
    - Click on the pod name
    - Click **Logs** tab
    - Look for Flask/Gunicorn startup messages:
    ```
    [INFO] Starting gunicorn 21.2.0
    [INFO] Listening at: http://0.0.0.0:8080
    [INFO] Using worker: sync
    ```

22. **Check for OpenSearch connection warning** (expected for Part 1):
    ```
    WARNING: OpenSearch not available - some features disabled
    INFO: Running in PDF-only mode
    ```
    
    > This is normal! We haven't deployed OpenSearch yet. The backend will work for direct LLM queries.

---

### Step 6.8: Test the Backend (Internal Access)

Since we didn't create a route, we need to test from inside the cluster:

23. **Create a test pod** (if not already done):
    ```bash
    oc run test-pod --image=registry.access.redhat.com/ubi9/ubi-minimal:latest --command -- sleep infinity
    ```

24. **Test the health endpoint**:
    ```bash
    oc exec test-pod -- curl http://rag-backend:8080/health
    ```
    
    Expected response:
    ```json
    {
      "status": "ok",
      "opensearch": "not configured",
      "llm_services": {
        "tinyllama": "available",
        "granite": "not deployed"
      }
    }
    ```

25. **Test LLM connection**:
    ```bash
    oc exec test-pod -- curl -X POST http://rag-backend:8080/api/generate \
      -H "Content-Type: application/json" \
      -d '{"prompt": "What is IBM Power?", "model": "tinyllama"}'
    ```

---

### Troubleshooting RAG Backend Deployment

**Build fails with dependency errors?**
- Check build logs for specific package failures
- PyTorch installation can be sensitive to versions
- Verify IBM Power wheels repository is accessible

**Pod crashes with OOMKilled?**
- Backend needs at least 4Gi memory for ML models
- Increase memory limits in deployment configuration
- Check cluster has available resources

**Can't connect to TinyLlama service?**
- Verify TinyLlama pod is running: `oc get pods`
- Check service exists: `oc get svc tinyllama-service`
- Test from backend pod: `oc exec rag-backend-xxx -- curl http://tinyllama-service:8080/health`

**OpenSearch connection errors?**
- Expected for Part 1! OpenSearch not deployed yet
- Backend will work for direct LLM queries
- We'll deploy OpenSearch in Part 2

---

### What's Next?

With RAG backend deployed, we can now:
- **Deploy Carbon UI**: Create the web interface with external access
- **Test Part 1 Demo**: Basic LLM queries showing hallucinations
- **Later**: Add OpenSearch for full RAG capabilities (Part 2)

> **Architecture So Far**:
> - ✅ TinyLlama LLM service (internal)
> - ✅ RAG Backend service (internal)
> - ⏳ Carbon UI (next - needs external route)
> - ⏳ OpenSearch (Part 2)

---

- **Later**: Deploy Granite 4.0 for more capable RAG responses (Part 3)

> **Important**: TinyLlama works standalone for Part 1. We'll add OpenSearch and RAG capabilities in the next steps.

---

## Step 6: Deploy RAG Backend Service

[To be continued...]
   - Resources: Deployment
   - Create a route: ✓ (checked)

4. **Build Configuration**
   - Builder Image: Dockerfile
   - Dockerfile path: `Dockerfile` (auto-detected)

5. **Click "Create"**

The build will take 10-15 minutes as it:
- Compiles llama.cpp with Power10 optimizations
- Downloads TinyLlama (~1.1GB)
- Downloads Granite 4.0 Micro (~2.5GB)

![LLM Build Progress](images/llm-build-progress-new.png)

### Option B: Command Line Deployment (Advanced)

```bash
# Login to OpenShift
oc login --token=<your-token> --server=<your-server>

# Create project
oc new-project llm-on-techzone

# Deploy from Git
cd Part1-Deploy-LLM
oc new-build --name llama-service --binary --strategy docker
oc start-build llama-service --from-dir=. --follow

# Create deployment
oc apply -f llama-deploy.yaml
oc apply -f llama-svc.yaml
oc apply -f llama-route.yaml
```

### Verify Deployment

1. **Check Build Status**
   - Topology view shows the build progress
   - Wait for dark blue ring (ready state)

2. **Access the LLM**
   - Click the arrow icon on the llama-service circle
   - Opens the llama.cpp web interface
   - Try asking: "What is IBM Power10?"

![LLM Interface](images/llm-interface-new.png)

### Model Switching

The deployment starts with **TinyLlama** by default. To switch models:

```bash
# Switch to Granite (better for RAG)
oc set env deployment/llama-service LLM_MODEL=granite

# Switch back to TinyLlama (faster, good for basic demos)
oc set env deployment/llama-service LLM_MODEL=tinyllama

# Verify which model is running
oc logs deployment/llama-service | grep "Starting with"
```

---

## Step 4: Deploy OpenSearch (Vector Database)

OpenSearch replaces the older Milvus setup with a simpler, more maintainable solution.

### Web Console Deployment

1. **Import from Git**
   - Click "+Add" → "Import from Git"
   - Git Repo URL: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
   - Context dir: `/Part3-RAG-Sales-Manual/opensearch-deployment`

2. **Configure**
   - Name: `opensearch`
   - Create route: ✓

3. **Create**

### Command Line Deployment (Advanced)

```bash
cd Part3-RAG-Sales-Manual/opensearch-deployment
oc apply -f opensearch-pvc.yaml
oc apply -f opensearch-deploy.yaml
oc apply -f opensearch-svc.yaml
```

---

## Step 5: Deploy RAG Backend

The backend handles PDF processing, vector search, and LLM integration.

### Web Console Deployment

1. **Import from Git**
   - Git Repo URL: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
   - Context dir: `/Part3-RAG-Sales-Manual/rag-backend`

2. **Configure**
   - Name: `rag-backend`
   - Create route: ✓

3. **Set Environment Variables** (after deployment)
   - Go to Deployment → Environment
   - Add:
     - `OPENSEARCH_HOST`: `opensearch.llm-on-techzone.svc.cluster.local`
     - `OPENSEARCH_PORT`: `9200`
     - `LLM_SERVICE_URL`: `http://llama-service.llm-on-techzone.svc.cluster.local:8080`
     - `CORS_ORIGIN`: `*` (for demo purposes)

### Command Line Deployment (Advanced)

```bash
cd Part3-RAG-Sales-Manual/rag-backend
./deploy.sh
```

---

## Step 6: Deploy Carbon UI

The modern web interface for the RAG demo.

### Web Console Deployment

1. **Import from Git**
   - Git Repo URL: `https://github.com/DSpurway/IBM-Power-RAG-Demos`
   - Context dir: `/Part3-RAG-Sales-Manual/carbon-rag-ui`

2. **Configure**
   - Name: `carbon-rag-ui`
   - Create route: ✓

3. **Set Environment Variables**
   - `NEXT_PUBLIC_RAG_BACKEND_URL`: (get from rag-backend route)
   - `NEXT_PUBLIC_LLM_SERVICE_URL`: (get from llama-service route)

### Get the UI URL

```bash
oc get route carbon-rag-ui -o jsonpath='{.spec.host}'
```

Open this URL in your browser to access the demo!

---

## Step 7: Load Sample Data

### Using the Web Interface

1. **Access Carbon UI** (from route URL)
2. **Navigate to "Load Data" tab**
3. **Click buttons to load PDFs**:
   - IBM Power S1012
   - IBM Power S1014
   - IBM Power S1022
   - IBM Power S1022s
   - IBM Power S1024

Each load takes 2-5 minutes. Watch the pod logs:

```bash
oc logs -f deployment/rag-backend
```

### Using Command Line (Advanced)

```bash
cd Part3-RAG-Sales-Manual/rag-backend
./load-sample-data.sh
```

---

## Step 8: Test the Demo

### Basic Query Flow

1. **Select a Server** from the dropdown (e.g., "S1022")
2. **Enter a Question**: "What processors are available?"
3. **Click "Retrieve Data"** - See relevant chunks from the manual
4. **Click "Build Prompt"** - See the context-aware prompt
5. **Click "Send to LLM"** - Get the AI-generated answer

### Demo Scenarios

**Scenario 1: Show Hallucination**
- Ask TinyLlama (without RAG): "What is Mr. Dursley's job?"
- It will make up an answer (hallucination)

**Scenario 2: Show RAG Accuracy**
- Use the Carbon UI with loaded data
- Ask: "What processors are in the S1022?"
- Shows accurate answer with source citations

**Scenario 3: Compare Models**
- Switch to Granite: `oc set env deployment/llama-service LLM_MODEL=granite`
- Ask the same question
- Compare response quality

---

## Troubleshooting

### Build Failures

**Problem**: Build times out or fails
**Solution**: 
```bash
oc start-build llama-service --follow
# Watch for specific errors
```

### CORS Errors

**Problem**: UI can't connect to backend
**Solution**:
```bash
oc set env deployment/rag-backend CORS_ORIGIN='*'
oc set env deployment/carbon-rag-ui NEXT_PUBLIC_RAG_BACKEND_URL='http://rag-backend-llm-on-techzone.apps...'
```

### Pod Crashes

**Problem**: Pods keep restarting
**Solution**:
```bash
oc logs deployment/rag-backend --previous
# Check for memory/resource issues
oc describe pod <pod-name>
```

### Slow Responses

**Problem**: LLM takes too long to respond
**Solution**:
- Switch to TinyLlama for faster responses
- Check if model is still loading: `oc logs deployment/llama-service`

---

## Advanced: CLI Setup

For users who prefer command-line deployment:

### Install oc CLI

1. **From OpenShift Console**:
   - Click "?" (help) → "Command Line Tools"
   - Download for your OS (Windows/Mac/Linux)

2. **Install**:
   - Windows: Extract and add to PATH
   - Mac: `brew install openshift-cli`
   - Linux: Extract to `/usr/local/bin`

### Login

```bash
# Get login command from OpenShift Console
# Click your username → "Copy login command"
oc login --token=<token> --server=<server>

# Verify
oc whoami
oc project llm-on-techzone
```

---

## Next Steps

- **Customize**: Add your own PDFs to the backend
- **Extend**: Try web scraping for live data
- **Scale**: Adjust resource limits for production
- **Migrate**: Move to EMEA-AI-SQUAD when ready

---

## Support

- **Documentation**: See README.md and QUICK_START.md
- **Issues**: Check pod logs and deployment status
- **Questions**: Contact David Spurway

**Version**: 1.0  
**Last Updated**: 2026-05-01  
**Repository**: https://github.com/DSpurway/IBM-Power-RAG-Demos
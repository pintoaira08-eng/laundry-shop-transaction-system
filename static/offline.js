const DB_NAME = "laundry_shop_offline";
const DB_VERSION = 1;

let dbPromise = null;

// Open the local database
function openDatabase() {
    if (dbPromise) return dbPromise;

    dbPromise = new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onupgradeneeded = function (event) {
            const database = event.target.result;

            if (!database.objectStoreNames.contains("orders")) {
                database.createObjectStore("orders", {
                    keyPath: "order_id"
                });
            }

            if (!database.objectStoreNames.contains("payments")) {
                database.createObjectStore("payments", {
                    keyPath: "payment_id"
                });
            }
        };

        request.onsuccess = function () {
            resolve(request.result);
        };

        request.onerror = function () {
            dbPromise = null;
            reject(request.error);
        };
    });

    return dbPromise;
}

// Generate a unique ID for offline orders
function generateOfflineOrderID() {
    const uniquePart = window.crypto?.randomUUID
        ? crypto.randomUUID().slice(0, 8).toUpperCase()
        : Math.random().toString(36).slice(2, 10).toUpperCase();

    return `LS-OFF-${Date.now()}-${uniquePart}`;
}

// Generate a unique ID for payment records
function generatePaymentID() {
    return window.crypto?.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

// Save a new order locally
async function addOfflineOrder(orderData) {
    const database = await openDatabase();

    const rates = {
        "Wash Only": 30,
        "Wash and Dry": 40,
        "Wash, Dry and Fold": 50
    };

    const rate = rates[orderData.service];
    const weight = Number(orderData.weight);

    if (!orderData.customer_name?.trim()) {
        throw new Error("Please enter the customer name.");
    }

    if (!orderData.contact_number?.trim() ||
        !/^\d+$/.test(orderData.contact_number)) {
        throw new Error("Please enter a valid contact number.");
    }

    if (!rate) {
        throw new Error("Please select a valid service.");
    }

    if (!Number.isFinite(weight) || weight <= 0) {
        throw new Error("Weight must be greater than zero.");
    }

    if (!orderData.due_date) {
        throw new Error("Please select a due date.");
    }

    const today = new Date();
    const todayString = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    if (orderData.due_date < todayString) {
        throw new Error("Due date cannot be in the past.");
    }

    const order = {
        order_id: generateOfflineOrderID(),
        customer_name: orderData.customer_name.trim(),
        contact_number: orderData.contact_number.trim(),
        service: orderData.service,
        weight: weight,
        total_amount: weight * rate,
        amount_paid: 0,
        change: 0,
        status: "Waiting",
        due_date: orderData.due_date,
        created_at: new Date().toISOString(),
        sync_status: "pending"
    };

    return new Promise((resolve, reject) => {
        const transaction = database.transaction("orders", "readwrite");
        const store = transaction.objectStore("orders");

        store.add(order);

        transaction.oncomplete = () => resolve(order);
        transaction.onerror = () => reject(transaction.error);
        transaction.onabort = () => reject(transaction.error);
    });
}

// Get all locally saved orders
async function getOfflineOrders() {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction("orders", "readonly");
        const request = transaction.objectStore("orders").getAll();

        request.onsuccess = () => {
            const orders = request.result || [];

            orders.sort((a, b) =>
                (b.created_at || "").localeCompare(a.created_at || "")
            );

            resolve(orders);
        };

        request.onerror = () => reject(request.error);
    });
}

// Find an order using its Order ID
async function findOfflineOrder(orderID) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction("orders", "readonly");
        const request = transaction.objectStore("orders")
            .get(orderID.trim().toUpperCase());

        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
    });
}

// Record a payment locally
async function addOfflinePayment(orderID, paymentAmount) {
    const database = await openDatabase();
    const amount = Number(paymentAmount);

    if (!Number.isFinite(amount) || amount <= 0) {
        throw new Error("Enter a valid payment amount.");
    }

    return new Promise((resolve, reject) => {
        const transaction = database.transaction(
            ["orders", "payments"],
            "readwrite"
        );

        const orderStore = transaction.objectStore("orders");
        const paymentStore = transaction.objectStore("payments");

        const request = orderStore.get(orderID.trim().toUpperCase());

        let updatedOrder = null;
        let payment = null;
        let validationError = null;

        request.onsuccess = function () {
            const order = request.result;

            if (!order) {
                validationError = "Order not found.";
                transaction.abort();
                return;
            }

            const remainingBalance =
                Number(order.total_amount) - Number(order.amount_paid);

            if (amount > remainingBalance + 0.000001) {
                validationError = "Payment cannot exceed the remaining balance.";
                transaction.abort();
                return;
            }

            order.amount_paid = Number(order.amount_paid) + amount;
            order.sync_status = "pending";

            payment = {
                payment_id: generatePaymentID(),
                order_id: order.order_id,
                amount: amount,
                payment_date: new Date().toISOString(),
                sync_status: "pending"
            };

            updatedOrder = order;

            orderStore.put(order);
            paymentStore.add(payment);
        };

        transaction.oncomplete = () => {
            resolve({
                order: updatedOrder,
                payment: payment
            });
        };

        transaction.onerror = () => {
            reject(validationError || transaction.error);
        };

        transaction.onabort = () => {
            reject(validationError || transaction.error);
        };
    });
}

// Get the payment history of an order
async function getOfflinePaymentHistory(orderID) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction("payments", "readonly");
        const request = transaction.objectStore("payments").getAll();

        request.onsuccess = () => {
            const payments = (request.result || [])
                .filter(payment => payment.order_id === orderID)
                .sort((a, b) =>
                    a.payment_date.localeCompare(b.payment_date)
                );

            resolve(payments);
        };

        request.onerror = () => reject(request.error);
    });
}

// Update an order's status locally
async function updateOfflineStatus(orderID, newStatus) {
    const database = await openDatabase();

    return new Promise((resolve, reject) => {
        const transaction = database.transaction("orders", "readwrite");
        const store = transaction.objectStore("orders");
        const request = store.get(orderID.trim().toUpperCase());

        let updatedOrder = null;
        let validationError = null;

        request.onsuccess = function () {
            const order = request.result;

            if (!order) {
                validationError = "Order not found.";
                transaction.abort();
                return;
            }

            const validTransition =
                (order.status === "Waiting" && newStatus === "Processing") ||
                (order.status === "Processing" && newStatus === "Ready");

            if (!validTransition) {
                validationError = "Invalid status transition.";
                transaction.abort();
                return;
            }

            order.status = newStatus;
            order.sync_status = "pending";

            updatedOrder = order;
            store.put(order);
        };

        transaction.oncomplete = () => resolve(updatedOrder);
        transaction.onerror = () => reject(validationError || transaction.error);
        transaction.onabort = () => reject(validationError || transaction.error);
    });
}

// Calculate the local sales summary
async function getOfflineSalesSummary() {
    const orders = await getOfflineOrders();

    return {
        total_orders: orders.length,
        total_sales: orders.reduce(
            (sum, order) => sum + Number(order.total_amount || 0), 0
        ),
        total_payments: orders.reduce(
            (sum, order) => sum + Number(order.amount_paid || 0), 0
        ),
        outstanding_balance: orders.reduce(
            (sum, order) =>
                sum + Number(order.total_amount || 0) -
                Number(order.amount_paid || 0), 0
        )
    };
}

// Make the functions available to the other app pages
window.LaundryOffline = {
    openDatabase,
    addOfflineOrder,
    getOfflineOrders,
    findOfflineOrder,
    addOfflinePayment,
    getOfflinePaymentHistory,
    updateOfflineStatus,
    getOfflineSalesSummary
};

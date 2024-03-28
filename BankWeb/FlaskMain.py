from flask import Flask, render_template, redirect, url_for, session, flash, request
from flask_mysqldb import MySQL
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'bankweb'

mysql = MySQL(app)
re_account_number = ''


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        birthdate = request.form['birthdate']
        gender = request.form['gender']
        phone_number = request.form['number']
        marital_status = request.form['status']
        occupation = request.form['occupation']
        employer = request.form['employer']
        email = request.form['email']
        password = request.form['pwd']
        re_password = request.form['re_password']

        # Check if email is already in use
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE Email = %s', (email,))
        email_count = cursor.fetchone()[0]
        cursor.close()

        if email_count > 0 and password != re_password:
            flash('⚠️ Email is already in use and Passwords do not match ', 'email_error')
            return redirect(url_for('register'))
        elif email_count > 0:
            flash('⚠️ Email is already in use.', 'email_error')
            return redirect(url_for('register'))
        elif password != re_password:
            flash('⚠️ Passwords do not match.', 'email_error')
            return redirect(url_for('register'))

            # Generate a random account number
        account_number = random.randint(100000000000, 999999999999)

        # Insert data into the database
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO users (Name, Address, Birthdate, Gender, Phone_Number, Marital_Status, Occupation, Employer, Email, Password, Account_Number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            (name, address, birthdate, gender, phone_number, marital_status, occupation, employer, email, password,
             account_number))
        cursor.execute(f'INSERT INTO balance (account_nummber) VALUES ( {account_number})')
        cursor.execute(f'INSERT INTO investments (account_number) VALUES ( {account_number})')
        cursor.execute(f'INSERT INTO loan (account_number) VALUES ({account_number})')
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('scan'))
    else:
        # Handle GET request
        return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_number = request.form['account_number']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE Account_Number = %s AND Password = %s", (account_number, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            flash('Log in success', 'uiu')
            session['account_number'] = account_number
            return redirect(url_for('home'))
        else:
            flash('Wrong account number or password', 'hj')
            return redirect(url_for('login'))  # Redirect back to the login page
    return render_template('index.html')


@app.route("/scan")
def scan():
    return render_template('scan.html')


@app.route("/home")
def home():
    if 'account_number' in session:
        # User is logged in, render the home page
        return render_template('home.html')
    else:
        # User is not logged in, redirect to the login page
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))


@app.route("/deposit", methods=['GET', 'POST'])
def deposit():
    if request.method == 'POST':
        # account_number = session['account_nummber']
        account_number = session.get('account_number')
        amount = request.form.get('depoMoney')
        amount = float(amount)
        cursor = mysql.connection.cursor()
        cursor.execute(f"UPDATE balance SET balance = balance + {amount} WHERE account_nummber = '{account_number}'")
        cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
        session['depoMoney'] = amount
        balance_sender = cursor.fetchone()
        for i in balance_sender:
            cursor.execute(
                f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '+{str(amount)}','{str(i)}' ,'Deposit')")
        mysql.connection.commit()
        flash('Deposit successful', 'success')
        cursor.close()
        return redirect(url_for('detran'))

    return render_template('deposit.html')

@app.route("/detran")
def detran():
    account_number = session.get('account_number')
    amount = session.get('depoMoney')
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"SELECT trans_bal, date_transac FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    rows = cursor.fetchall()
    for row in rows:
        trans_bal, date_transac = row
        date = row[1]
        trans_bal = float(row[0])
        print(date, trans_bal)
        return render_template("detran.html", date_transac=date, trans_bal=trans_bal,amount=amount)


@app.route("/transactions")
def transactions():
    account_number = session.get('account_number')
    cursor = mysql.connection.cursor()
    cursor.execute(f"SELECT * FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    data = cursor.fetchall()

    transaction_list = []
    for row in data:
        transaction = {
            'date': str(row[4]),
            'time': str(row[5]),
            'description': row[1],
            'amount': row[2],
            'balance': row[3],
            # Add other fields as needed
        }
        transaction_list.append(transaction)
    cursor.close()
    return render_template("transactions.html", transaction=transaction_list)


@app.route("/transfer", methods=['POST', 'GET'])
def transfer():
    if request.method == 'POST':
        global amount
        global re_account_number
        account_number = session.get('account_number')
        re_account_number = request.form['re_account_number']
        amount = float(request.form['tranMoney'])

        # Check if sender has sufficient balance
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
        result = cursor.fetchone()
        if result is not None:
            balance = result[0]
            if balance < amount:
                flash('Insufficient balance.', 'error')
            else:
                cursor.execute(
                    f"UPDATE balance SET balance = balance - {amount} WHERE account_nummber = '{account_number}'")
                cursor.execute(
                    f"UPDATE balance SET balance = balance + {amount} WHERE account_nummber = '{re_account_number}'")
                cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{re_account_number}'")
                balance_reciever = cursor.fetchone()
                cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
                balance_sender = cursor.fetchone()
                for i in balance_sender:
                    cursor.execute(
                        f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '-{str(amount)}','{str(i)}' ,'Transfer')")
                for i in balance_reciever:
                    cursor.execute(
                        f"INSERT INTO transaction (account_nummber, amount,trans_bal,type) VALUES ({re_account_number}, '+{str(amount)}','{str(i)}' , 'Received')")
                mysql.connection.commit()
                cursor.close()
                return redirect(url_for('transtran'))

        else:
            flash('Account not found.', 'error')

    return render_template('transfer.html')

@app.route("/transtran")
def transtran():
    account_number = session.get('account_number')
    global re_account_number
    global amount
    cursor = mysql.connection.cursor()
    cursor.execute(
        f"SELECT trans_bal, date_transac FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    rows = cursor.fetchall()
    for row in rows:
        trans_bal, date_transac = row
        date = row[1]
        trans_bal = float(row[0])
        print(date, trans_bal)
        return render_template("transtran.html", date_transac=date, trans_bal=trans_bal,re_account_number=re_account_number,amount=amount)
    return render_template("transtran.html")

@app.route("/withdraw", methods=['POST', 'GET'])
def withdraw():
    if request.method == 'POST':
        account_number = session.get('account_number')
        amount = request.form.get('withMoney')
        cursor = mysql.connection.cursor()
        cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
        balance = cursor.fetchone()[0]


        try:
            amount = float(amount)
            if(balance > amount):
                cursor.execute(
                    f"UPDATE balance SET balance = balance - {amount} WHERE account_nummber = '{account_number}'")
                cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
                session['withMoney'] = amount
                balance_sender = cursor.fetchone()
                for i in balance_sender:
                    cursor.execute(
                        f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '-{str(amount)}','{str(i)}' ,'Withdraw')")

                mysql.connection.commit()
                flash('Withdraw successful', 'success')

            else:
                flash('Not enough balance.', 'error')

        except Exception as e:
            flash('An error occurred while processing your withdraw.', 'error')
            print(f"Error: {e}")
        finally:
            cursor.close()

        return redirect(url_for('withtran'))  # , account_number=account_number))

    return render_template('withdraw.html')

@app.route("/withtran")
def withtran():
    account_number = session.get('account_number')
    cursor = mysql.connection.cursor()
    amount = session.get("withMoney")
    cursor.execute(
        f"SELECT trans_bal, date_transac FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    rows = cursor.fetchall()
    cursor.close()
    for row in rows:
        trans_bal, date_transac = row
        date = row[1]
        trans_bal = float(row[0])
        print(date, trans_bal)
        return render_template("withtran.html", date_transac=date, trans_bal=trans_bal, amount=amount)
    else:
        return "No payment found for this account number", 404




@app.route("/balance")
def balance():
    account_number = session.get('account_number')
    cursor = mysql.connection.cursor()
    cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
    balance = cursor.fetchone()
    for i in balance:
        print(i)
        return render_template("balance.html", balance=str(i))


@app.route("/paybills", methods=['GET', 'POST'])
def paybills():
    if request.method == 'POST':
        account_number = session.get('account_number')
        description = request.form['description']
        amount = float(request.form['pay_amount'])

        cursor = mysql.connection.cursor()

        # Check if the account number exists
        cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = {account_number}")
        balance = cursor.fetchone()[0]

        if float(balance) >= amount:
            balance -= amount
            cursor.execute(f"UPDATE balance SET balance = {balance} WHERE account_nummber = {account_number}")

            cursor.execute(f"SELECT balance FROM balance WHERE account_nummber = '{account_number}'")
            balance_sender = cursor.fetchone()
            for i in balance_sender:
                cursor.execute(f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '-{str(amount)}','{str(i)}' ,'Paybills/{description}')")
            session['description'] = description
            session['amount'] = amount
            mysql.connection.commit()
            cursor.close()
            flash('Bill paid successfully', 'success')
            return redirect(url_for('tconfirmation'))
        else:
            flash('Insufficient balance', 'danger')

    return render_template('paybills.html')

@app.route("/tconfirmation")
def tconfirmation():
    cursor = mysql.connection.cursor()
    account_number = session.get('account_number')
    description = session.get('description')
    amount = session.get('amount')
    cursor.execute(
        f"SELECT trans_bal, date_transac FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    rows = cursor.fetchall()
    cursor.close()
    for row in rows:
        trans_bal, date_transac = row
        date = row[1]
        trans_bal = float(row[0])
        print(date, trans_bal)
        return render_template('tconfirmation.html', date_transac=date,trans_bal=trans_bal,description=description, amount=amount)
    else:
        return "No payment found for this account number", 404

@app.route('/investment', methods=['GET','POST'])
def investment():
    if request.method == 'POST':
        account_number = session.get("account_number")
        plan = request.form['plan']
        amount = request.form['amount']
        float(amount)
            # Get the first element of the tuple (account_number)
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE investments SET plan = %s, amount = amount - %s WHERE account_number = %s",
                       (plan,amount, account_number))
        cursor.execute(f"UPDATE balance SET balance = balance - {amount} WHERE account_nummber = '{account_number}'")
        cursor.execute("SELECT balance FROM balance WHERE account_nummber = %s", (account_number,))
        session['plan'] = plan
        session['amount'] = amount
        mysql.connection.commit()
        investor = cursor.fetchone()

        for i in investor:
            cursor.execute(f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '-{str(amount)}','{str(i)}' ,'Investment/{plan}')")
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('lconfirmation'))

    return render_template('investment.html')

@app.route("/lconfirmation")
def lconfirmation():
    cursor = mysql.connection.cursor()
    account_number = session.get('account_number')
    plan = session.get('plan')
    amount = session.get('amount')
    cursor.execute(f"SELECT trans_bal, date_transac FROM transaction WHERE account_nummber = '{account_number}' ORDER BY time_transac DESC")
    rows = cursor.fetchall()
    cursor.close()
    for row in rows:
        trans_bal, date_transac = row
        date_transac = row[1]
        return render_template('lconfirmation.html',   plan =plan , amount  = amount,invest_date = date_transac)


@app.route('/loans', methods=['GET', 'POST'])
def loans():
    if request.method == 'POST':
        account_number = session.get('account_number')
        loan_type = request.form['loanType']
        amount = float(request.form['amount'])
        term = int(request.form['term'])

        interest_rate = get_interest_rate(loan_type)
        monthly_interest_rate = interest_rate / 12 / 100
        if monthly_interest_rate != 0:
            monthly_payment = (amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate) ** -term)
        else:
            monthly_payment = amount / term

        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "UPDATE loan SET loan_type=%s, loan_amount=%s, monthly_payment=%s, loan_term=%s WHERE account_number=%s",
                (loan_type, amount, monthly_payment, term, account_number)
            )
            cursor.execute("UPDATE balance SET balance = balance + %s WHERE account_nummber = %s",
                           (amount, account_number))
            cursor.execute("SELECT balance FROM balance WHERE account_nummber = %s", (account_number,))
            investor = cursor.fetchone()
            for i in investor:
                cursor.execute(
                    f"INSERT INTO transaction (account_nummber, amount, trans_bal,type) VALUES ({account_number}, '+{str(amount)}','{str(i)}' ,'Loans/{loan_type}')")

            mysql.connection.commit()
        finally:
            cursor.close()

        return redirect(url_for('loantran', loan_type=loan_type, amount=amount, term=term, monthly_payment=monthly_payment))

    return render_template('loans.html')

def get_interest_rate(loan_type):
    if loan_type == 'Personal':
        return 5.5
    elif loan_type == 'Home':
        return 4.5
    elif loan_type == 'Auto':
        return 6.0
    else:
        raise ValueError("Invalid loan type")

@app.route('/loantran')
def loantran():
    account_number = session.get('account_number')

    cursor = mysql.connection.cursor()
    cursor.execute(f"SELECT * FROM loan Where account_number = '{account_number}' ")
    loans = cursor.fetchone()  # Fetch the first (and only) row
    cursor.close()

    loan_type = loans[1]
    loan_amount = loans[2]
    loan_term = loans[3]
    monthly_payment = loans[4]

    return render_template('loantran.html',loan_type=loan_type,loan_amount=loan_amount,loan_term=loan_term,monthly_payment=monthly_payment)

@app.route("/accounts")
def accounts():
    return render_template("accounts.html")


@app.route("/update")
def update():
    return render_template("update.html")


@app.route("/support")
def support():
    return render_template("support.html")


@app.route("/help")
def help():
    return render_template("help.html")


@app.route("/menu")
def menu():
    return render_template("menu.html")



@app.route("/terms")
def terms():
    return render_template("terms.html")









@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)

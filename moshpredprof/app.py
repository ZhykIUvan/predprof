import sqlite3
from flask import Flask, request, render_template, url_for, redirect

app = Flask(__name__)

admin_code = "1234"
just_user_code = "1111"
is_logged = False


def convert_inventory_into_list(type):
    conn = get_db_connection()
    cursor = conn.cursor()

    inventory = {}
    inventory_names = cursor.execute('SELECT db_name, COUNT(db_name) FROM db_inventory '
                                     'WHERE db_type = ? GROUP BY db_name', (type,)).fetchall()
    for one in inventory_names:
        things_by_name = cursor.execute('SELECT * FROM db_inventory WHERE db_type = ? AND db_name = ?',
                                         (type, one['db_name'],)).fetchall()
        things = []
        if type == "usefull":
            for thing in things_by_name:
                user_name = cursor.execute('SELECT db_name FROM db_users WHERE db_login = ?',
                                           (thing['db_user'],)).fetchone()
                things.append({'thing': thing, 'user_name': user_name['db_name']})
        else:
            things = things_by_name
        inventory[one['db_name']] = {'count': one['COUNT(db_name)'], 'things': things}

    conn.commit()
    conn.close()

    return inventory


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS db_users (db_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'db_user_type TEXT NOT NULL, db_login TEXT NOT NULL, db_password TEXT NOT NULL, '
                   'db_name TEXT NOT NULL, db_work TEXT, db_id_inventory TEXT)')

    cursor.execute('CREATE TABLE IF NOT EXISTS db_inventory (db_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'db_type TEXT NOT NULL, db_name TEXT NOT NULL, db_user TEXT, db_problem_description TEXT)')

    cursor.execute('CREATE TABLE IF NOT EXISTS db_bought_inventory (db_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'db_type TEXT NOT NULL, db_data DATA NOT NULL, db_name TEXT NOT NULL, db_count INT NOT NULL,'
                   ' db_producer TEXT NOT NULL, db_price INT NOT NULL)')

    conn.commit()
    conn.close()


init_db()


# -------------- Вход и регистрация --------------

@app.route('/', methods=['GET', 'POST'])
def index():
    global is_logged

    is_login = False
    user = None
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']

        if len(login) == 0 or len(password) == 0:
            return render_template('index.html', error="Все поля должны быть заполнены")

        conn = get_db_connection()
        cursor = conn.cursor()
        users = cursor.execute('SELECT * FROM db_users').fetchall()
        for one in users:
            if login == one['db_login']:
                is_login = True
                user = one
                break
        conn.commit()
        conn.close()

        if not is_login:
            return render_template('index.html', error="Логин не нйден")

        if password != user['db_password']:
            return render_template('index.html', error="Неверный пароль")

        if user['db_user_type'] == "admin":
            file = "admin.html"
        else:
            file = "just_user.html"

        is_logged = True
        return render_template(file, user=user)

    else:
        return render_template('index.html')


@app.route('/register<user_type>', methods=['GET', 'POST'])
def register(user_type):
    global is_logged
    if user_type == "admin":
        file = "admin.html"
        work_text = "Ваша должность"
        user_name = "Админа"
        true_code = admin_code
    else:
        file = "just_user.html"
        work_text = "Введите класс с буквой"
        user_name = "Пользователя"
        true_code = just_user_code

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()

        is_error = False
        errors = []

        login = request.form['login']
        password1 = request.form['password1']
        password2 = request.form['password2']
        name = request.form['name']
        work = request.form['work']
        code = request.form['code']

        users = cursor.execute('SELECT db_login FROM db_users').fetchall()

        for one in [login, password1, password2, name, code]:
            if len(one) == 0:
                is_error = True
                errors.append("Некоторые поля оставлены пустыми")
                break

        for one in users:
            if login in one['db_login']:
                is_error = True
                errors.append("Логин знят")
                break

        if password1 != password2:
            is_error = True
            errors.append("Пароли не свпадают")

        if code != true_code:
            is_error = True
            errors.append(f"Неверный код {user_name}")

        if is_error:
            conn.close()
            return render_template('register.html', user=user_name, work_text=work_text,
                                   error=errors[0])
        else:
            conn.execute('INSERT INTO db_users (db_user_type, db_login, db_password, db_name, db_work) '
                         ' VALUES (?, ?, ?, ?, ?)', (user_type, login, password1, name, work))
            conn.commit()
            user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (login,)).fetchone()
            conn.close()
            is_logged = True
            return render_template(file, user=user)

    else:
        return render_template('register.html', user_name=user_name, work_text=work_text)


# -------------- Вход и регистрация --------------


# -------------- users --------------
@app.route('/admin<user_login>')
def admin(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        conn.commit()
        conn.close()
        return render_template('admin.html', user=user)
    else:
        return redirect(url_for('index'))


@app.route('/just_user<user_login>')
def just_user(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        conn.commit()
        conn.close()
        return render_template('just_user.html', user=user)
    else:
        return redirect(url_for('index'))


# -------------- users --------------


# -------------- inventory --------------
@app.route('/inventory_all<user_login>')
def inventory_all(user_login):
    if is_logged:
        null_all = ""
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()

        inventory_names = cursor.execute('SELECT db_name, COUNT(db_name) FROM db_inventory GROUP BY db_name').fetchall()

        inventory = {}
        for name in inventory_names:
            things_free = cursor.execute('SELECT * FROM db_inventory WHERE db_name = ? AND db_type = ?',
                                         (name['db_name'], "free")).fetchall()
            count_free = len(things_free)

            things_usefull_whithout_user = cursor.execute('SELECT * FROM db_inventory WHERE db_name = ? AND db_type = ?',
                                                          (name['db_name'], "usefull")).fetchall()
            count_usefull = len(things_usefull_whithout_user)
            things_usefull = []
            for thing in things_usefull_whithout_user:
                user_name = cursor.execute('SELECT db_name FROM db_users WHERE db_login = ?',
                                           (thing['db_user'],)).fetchone()
                things_usefull.append({'thing': thing, 'user_name': user_name['db_name']})

            things_broken = cursor.execute('SELECT * FROM db_inventory WHERE db_name = ? AND db_type = ?',
                                           (name['db_name'], "broken")).fetchall()
            count_broken = len(things_broken)

            inventory[name['db_name']] = {'count': name['COUNT(db_name)'],
                                          'free': {'count': count_free, 'things': things_free},
                                          'usefull': {'count': count_usefull, 'things': things_usefull},
                                          'broken': {'count': count_broken, 'things': things_broken}}

        if len(inventory) == 0:
            null_all = "Нет инвентаря"
        conn.commit()
        conn.close()
        return render_template('inventory_all.html', user=user, inventory=inventory, null_all=null_all)
    else:
        return redirect(url_for('index'))


@app.route('/inventory_free<user_login>')
def inventory_free(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        conn.close()

        null_free = ""
        inv_free = convert_inventory_into_list("free")
        if len(inv_free) == 0:
            null_free = "Нет свободного инвентаря!"

        return render_template('inventory_free.html', user=user, inv_free=inv_free, null_free=null_free)
    else:
        return redirect(url_for('index'))


@app.route('/inventory_usefull<user_login>')
def inventory_usefull(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        conn.close()

        null_usefull = ""
        inv_usefull = convert_inventory_into_list("usefull")
        if len(inv_usefull) == 0:
            null_usefull = "Нет закреплённого инвентаря!"

        return render_template('inventory_usefull.html', user=user, inv_usefull=inv_usefull,
                               null_usefull=null_usefull)
    else:
        return redirect(url_for('index'))


@app.route('/inventory_broken<user_login>')
def inventory_broken(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        conn.close()

        null_broken = ""
        inv_broken = convert_inventory_into_list("usefull")
        if len(inv_broken) == 0:
            null_broken = "Нет сломанного инвентаря!"

        return render_template('inventory_broken.html', user=user, inv_broken=inv_broken, null_broken=null_broken)
    else:
        return redirect(url_for('index'))


# -------------- inventory --------------


@app.route('/show_users<user_login>')
def show_users(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()
        admins = cursor.execute('SELECT * FROM db_users WHERE db_user_type = "admin" AND NOT db_login = ?',
                                (user_login,)).fetchall()
        just_users = cursor.execute('SELECT * FROM db_users WHERE db_user_type = "just_user"').fetchall()
        conn.commit()
        conn.close()
        return render_template('show_users.html', user=user, admins=admins, just_users=just_users)
    else:
        return redirect(url_for('index'))


@app.route('/bought_plan')
def bought_plan():
    return


@app.route('/reports')
def reports():
    return


@app.route('/application')
def application():
    return


@app.route('/message_about_break')
def message_about_break():
    return


@app.route('/add_inventory<user_login>', methods=['GET', 'POST'])
def add_inventory(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()

        if request.method == 'POST':
            name = request.form['name']
            count = request.form['count']
            try:
                count = int(count)
            except:
                conn.commit()
                conn.close()
                return render_template('add_inventory.html', user=user, error="Невозможное значение колличества")
            if count <= 0:
                conn.commit()
                conn.close()
                return render_template('add_inventory.html', user=user, error="Невозможное значение колличества")

            list_id = []
            for i in range(count):
                cursor.execute('INSERT INTO db_inventory (db_type, db_name) VALUES ("free", ?)', (name,))
                list_id.append(cursor.lastrowid)

            conn.commit()
            conn.close()
            list_id_text = f"Обязательно сохраните ID-номера добавленного инвентаря \"{name}\" ({count} шт.):"
            return render_template('add_inventory.html', user=user, list_id_text=list_id_text, list_id=list_id)

        conn.commit()
        conn.close()
        return render_template('add_inventory.html', user=user)
    else:
        return redirect(url_for('index'))


@app.route('/delete_inventory<user_login>', methods=['GET', 'POST'])
def delete_inventory(user_login):
    if is_logged:
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()

        if request.method == 'POST':
            list_id = request.form['list_id'].split(" ")

            is_error = False
            for id in list_id:
                try:
                    a = int(id)
                    id = a
                except:
                    is_error = True
                lenght = len(cursor.execute('SELECT * FROM db_inventory WHERE db_id = ?', (id,)).fetchall())
                if id <= 0 or lenght == 0:
                    is_error = True
                if is_error:
                    return render_template('delete_inventory.html', user=user,
                                           error="Ошибка ввода", delete_list={})

            delete_list = {'free and broken': [], 'usefull': []}
            for id in list_id:
                thing = cursor.execute('SELECT * FROM db_inventory WHERE db_id = ?', (id,)).fetchone()
                if thing['db_type'] == "usefull":
                    user = cursor.execute('SELECT db_name FROM db_users WHERE db_login = ?', (thing['db_user'],)).fetchone()
                    delete_list['usefull'].append({'thing': thing, 'user_name': user['db_name']})
                else:
                    delete_list['free and broken'].append(thing)

            conn.commit()
            conn.close()

            list_id_str = " ".join(str(id) for id in list_id)
            return render_template('repeat_delete_inventory.html', user=user, delete_list=delete_list, list_id=list_id_str)

        conn.commit()
        conn.close()
        return render_template('delete_inventory.html', user=user, delete_list={})
    else:
        return redirect(url_for('index'))


@app.route('/repeat_delete_inventory<parameter>')
def repeat_delete_inventory(parameter):
    if is_logged:
        user_login, list_id = parameter.split(":")

        conn = get_db_connection()
        cursor = conn.cursor()

        user = cursor.execute('SELECT * FROM db_users WHERE db_login = ?', (user_login,)).fetchone()

        delete_list = {'free and broken': [], 'usefull': []}
        for id in list_id.split(" "):
            thing = cursor.execute('SELECT * FROM db_inventory WHERE db_id = ?', (id,)).fetchone()
            if thing['db_type'] == "usefull":
                user = cursor.execute('SELECT db_name FROM db_users WHERE db_login = ?', (thing['db_user'],)).fetchone()
                delete_list['usefull'].append({'thing': thing, 'user_name': user['db_name']})
            else:
                delete_list['free and broken'].append(thing)

        for id in list_id.split(" "):
            cursor.execute('DELETE FROM db_inventory WHERE db_id = ?', (id,))

        conn.commit()
        conn.close()
        return render_template('delete_inventory.html', user=user, delete_list=delete_list, delete_text="Вы удалили сдедующий инвентарь:")
    else:
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()

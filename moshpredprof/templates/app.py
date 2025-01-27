from flask import Flask, request, render_template
app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        if login == password:
            return render_template('admin.html')
        return render_template('index.html', post="Ошибка")
    return render_template('index.html', post="")



if __name__ == '__main__':
    app.run()

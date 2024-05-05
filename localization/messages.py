from schemas.order_status import OrderStatus

DEFAULT_LANG = 'en'


class LocalizedMessage(dict):
    def __init__(self, arg: dict):
        if DEFAULT_LANG not in arg.keys():
            raise ValueError(f"{DEFAULT_LANG} key must be set")
        super().__init__(arg)

    def __getitem__(self, __key):
        try:
            return super().__getitem__(__key)
        except KeyError:
            return super().__getitem__(DEFAULT_LANG)


MESSAGES = {
    'help': {
        'en': "Supported commands:\n"
              "/build - create an order\n"
              "/status - get your order status\n"
              "/cancel - cancel your order\n"
              "/help - get this help",
        'ru': "Доступные команды:\n"
              "/build - создать заказ\n"
              "/status - показать статус заказа\n"
              "/cancel - отменить заказ\n"
              "/help - показать эту справку",
        'be': "Даступныя каманды:\n"
              "/build - стварыць замову\n"
              "/status - паказаць статус замовы\n"
              "/cancel - скасаваць замову\n"
              "/help - паказаць гэтую даведку",
        'uk': "Доступні команди:\n"
              "/build - створити замовлення\n"
              "/status - показати статус замовлення\n"
              "/cancel - скасувати замовлення\n"
              "/help - показати цю довідку",
    },
    'no-orders-yet': {
        'en': "You have not yet started setting up your version of Partisan Telegram.",
        'ru': "Вы ещё не начали настраивать Вашу версию Партизанского Телеграма.",
        'be': "Вы яшчэ не пачалі настройваць Вашую версію Партызанскага Тэлеграма.",
        'uk': "Ви ще не почали настроювати Вашу версію Партизанського Телеграма.",
    },
    'canceled': {
        'en': "Your order is canceled. Send /build to configure your version of Partisan Telegram again or click the button below this message to clear messages.",
        'ru': "Ваш заказ отменён. Отправьте /build для повторной настройки Вашей версии Партизанского Телеграма или нажмите кнопку под этим сообщением для очистки переписки.",
        'be': "Вашая замова скасаваная. Дашліце /build для паўторнай налады Вашай версіі Партызанскага Тэлеграма або націсніце кнопку пад гэтым паведамленнем для ачысткі перапіскі.",
        'uk': "Ваше замовлення скасувано. Надішліть /build для повторного налаштування Вашої версії Партизанського Телеграма або натисніть кнопку під цим повідомленням для очищення листування.",
    },
    'queued': {
        'en': 'Your order is queued for build.',
        'ru': 'Ваш заказ поставлен в очередь на сборку.',
        'be': 'Вашая замова пастаўленая ў чаргу на зборку.',
        'uk': 'Ваше замовлення поставлено в чергу на збірку.',
    },
    'app-name-too-long': {
        'en': "App name is too long. The name must not be longer than {0} characters.",
        'ru': "Слишком длинное название приложения. Название должно быть не длинее {0} символов.",
        'be': "Занадта доўгая назва дадатка. Назва мае быць не даўжэйшай за {0} cімвалаў.",
        'uk': "Занадто довга назва додатку. Назва має бути не довше за {0} символів.",
    },
    'app-name-is': {
        'en': "App name is <b>{0}</b>.",
        'ru': "Название приложения – <b>{0}</b>.",
        'be': "Назва дадатка – <b>{0}</b>.",
        'uk': "Назва додатку – <b>{0}</b>.",
    },
    'app-id-about': {
        'en': "Every Android app has an ID (<i>applicationId</i>), which uniquely identifies the app on the device.",
        'ru': "У каждого Android приложения есть ID (<i>applicationId</i>), который уникально определяет приложение на устройстве.",
        'be': "Кожны Android дадатак мае ID (<i>applicationId</i>), які унікальна вызначае дадатак на прыладзе.",
        'uk': "Кожен Android додаток має ID (<i>applicationId</i>), який унікально визначає додаток на пристрої.",
    },
    'ask-app-id': {
        'en': "Please select application ID or enter it from keyboard. ",
        'ru': "Пожалуйста, выберите ID приложения или введите с клавиатуры. ",
        'be': "Калі ласка, выберыце ID дадатка альбо ўвядзіце з клавіятуры. ",
        'uk': "Будь ласка, виберіть ID додатку або введіть із клавіатури. ",
    },
    'custom-app-id': {
        'en': 'Enter...',
        'ru': 'Ввести...',
        'be': 'Увесьці...',
        'uk': 'Ввести...',
    },
    'ask-custom-app-id': {
        'en': "Please enter the <i>applicationId</i>.\n"
              "Example of a correct ID: <code>{0}</code>.",
        'ru': "Пожалуйста, введите <i>applicationId</i>.\n"
              "Пример правильного ID: <code>{0}</code>.",
        'be': "Калі ласка, увядзіце <i>applicationId</i>.\n"
              "Прыклад правільнага ID: <code>{0}</code>.",
        'uk': "Будь ласка, введіть <i>applicationId</i>.\n"
              "Приклад правильного ID: <code>{0}</code>.",
    },
    'invalid-app-id': {
        'en': "Invalid application ID.\n"
              "See more information <a href=\"{0}\">here</a>.",
        'ru': "Недопустимый ID приложения.\n"
              "Смотрите больше информации <a href=\"{0}\">здесь</a>.",
        'be': "Недапушчальны ID дадатка.\n"
              "Глядзіце больш інфармацыі <a href=\"{0}\">тут</a>.",
        'uk': "Недопустимий ID додатку.\n"
              "Дивіться більше інформаціі <a href=\"{0}\">тут</a>.",
    },
    'app-id-is': {
        'en': "<i>applicationId</i> is {0}",
        'ru': "<i>applicationId</i> приложения — {0}",
        'be': "<i>applicationId</i> дадатка — {0}",
        'uk': "<i>applicationId</i> додатку — {0}",
    },
    'ask-icon': {
        'en': "Please upload the image you want to have as the app's icon.",
        'ru': "Пожалуйста, загрузите изображение, которую хотите сделать иконкой приложения.",
        'be': "Калі ласка, загрузіце выяву, якую хочаце зрабіць іконкай дадатка.",
        'uk': "Будь ласка, завантажте зображення, яке хочете зробити іконкою додатку.",
    },
    'file-too-big': {
        'en': "Your file is too big. Please send a file smaller than {} MB.",
        'ru': "Ваш файл слишком большой. Пожалуйста, загрузите файл меньше {} МБ.",
        'be': "Ваш файл занадта вялікі. Калі ласка, загрузіце файл меншы за {} МБ.",
        'uk': "Ваш файл занадто великий. Будь ласка, завантажте файл менший за {} МБ.",
    },
    'file-is-not-image': {
        'en': "The file is not an image.",
        'ru': "Файл не является изображением.",
        'be': "Файл не з'яўляецца выявай.",
        'uk': "Файл не є зображенням.",
    },
    'grouped-images-are-not-allowed': {
        'en': "You only need to send one image.",
        'ru': "Необходимо прислать только одно изображение.",
        'be': "Неабходна даслаць толькі адну выяву.",
        'uk': "Необхідно надіслати лише одне зображення.",
    },
    'request-confirmation': {
        'en': "Your order is\n{0} ({1})\nSchedule the build?",
        'ru': "Ваш заказ\n{0} ({1})\nЗапланировать сборку?",
        'be': "Вашая замова\n{0} ({1})\nЗапланаваць зборку?",
        'uk': "Ваше замовлення\n{0} ({1})\nЗапланувати збірку?",
    },
    'confirmed': {
        'en': "Your order is confirmed.",
        'ru': "Ваш заказ подтвержён.",
        'be': "Вашая замова пацверджаная.",
        'uk': "Ваше замовлення підтверджено.",
    },
    'awaiting-build': {
        'en': "Your order is awaiting build. If you want to cancel the build please send /cancel.",
        'ru': "Ваш заказ ожидает сборки. Если вы хотите отменить сборку, пожалуйста, отправьте /cancel.",
        'be': "Вашая замова чакае зборкі. Калі вы хаціце скасаваць зборку, калі ласка, дашліце /cancel.",
        'uk': "Ваше замовлення чекає на збірку. Якщо ви хочете скасувати збірку, будь ласка, відправте /cancel.",
    },
    'build-started': {
        'en': "Build of your order is started, it will take some time.",
        'ru': "Сборка вашего заказа началась, она займёт некоторое время.",
        'be': "Зборка вашае замовы пачалася, яна зойме некаторы час.",
        'uk': "Збірка вашого замовлення почалася, вона зойме деякий час.",
    },
    'is-building': {
        'en': "Your order is being built.",
        'ru': "Ваш заказ собирается.",
        'be': "Вашая замова збіраецца.",
        'uk': "Ваше замовлення збирається."
    },
    'build-failed': {
        'en': "Build failed.",
        'ru': "Сборка не удалась.",
        'be': "Зборка не ўдалася.",
        'uk': "Збірка не вдалася."
    },
    'retry-build': {
        'en': "Retry build",
        'ru': "Попробовать заново",
        'be': "Паспрабаваць нанова",
        'uk': "Спробувати заново",
    },
    'cancel-order': {
        'en': "Cancel order",
        'ru': "Отменить заказ",
        'be': "Скасаваць замову",
        'uk': "Скасувати замовлення",
    },
    'welcome': {
        'en': "Welcome! Please send /build to start setting up your version of Partisan Telegram.",
        'ru': "Приветствую! Пожалуйста, отправьте /build для начала настройки Вашей версии Партизанского Телеграма.",
        'be': "Вітаю! Калі ласка, дашліце /build для пачатку наладкі Вашай версіі Партызанскага Тэлеграма.",
        'uk': "Вітаю! Будь ласка, надішліть /build для початку налаштування Вашої версії Партизанського Телеграма.",
    },
    'ask-for-app-name': {
        'en': "How do you want to call your app?",
        'ru': "Как вы хотите назвать приложение?",
        'be': "Як вы хочаце назваць дадатак?",
        'uk': "Як ви хочете назвати додаток?",
    },
    'you-already-started-building': {
        'en': "You have already started setting up the app, {0}.",
        'ru': "Вы уже начали настраивать приложение, {0}.",
        'be': "Вы ўжо пачалі наладжваць дадатак, {0}.",
        'uk': "Ви вже почали налаштовувати додаток, {0}.",
    },
    'status-configuring': {
        'en': "You are setting up your Partisan Telegram.",
        'ru': "Вы настраиваете Ваш Партизанский Телеграм.",
        'be': "Вы настройваеце Ваш Партызанскі Тэлеграм.",
        'uk': "Ви налаштовуєте Ваш Партизанський Телеграм.",
    },
    'status-building': {
        'en': "Your Partisan Telegram is building.",
        'ru': "Ваш Партизанский Телеграм собирается.",
        'be': "Ваш Партызанскі Тэлеграм збіраецца.",
        'uk': "Ваш Партизанський Телеграм збирається.",
    },
    'status-queued': {
        'en': "Your Partisan Telegram is in the queue.",
        'ru': "Ваш Партизанский Телеграм находится в очереди.",
        'be': "Ваш Партызанскі Тэлеграм знаходзіцца ў чарзе.",
        'uk': "Ваш Партизанський Телеграм перебуває у черзі.",
    },
    'status-completed': {
        'en': "The build of your Partisan Telegram is completed or cancelled.",
        'ru': "Сборка Вашего Партизанского Телеграма завершена или отменена.",
        'be': "Зборка Вашага Партызанскага Тэлеграма завершана або адменена.",
        'uk': "Складання Вашого Партизанського Телеграма завершено або скасовано.",
    },
    'status-unknown': {
        'en': "Status unknown.",
        'ru': "Статус неизвестен.",
        'be': "Статус невядомы.",
        'uk': "Статус невідомий.",
    },
    'yes': {
        'en': "Yes",
        'ru': "Да",
        'be': "Так",
        'uk': "Так",
    },
    'no': {
        'en': "No",
        'ru': "Нет",
        'be': "Не",
        'uk': "Ні"
    },
    'status-desc': {
        'en': "Display your order status",
        'ru': "Показать статус вашего заказа",
        'be': "Паказаць статус вашай замовы",
        'uk': "Показати статус вашого замовлення"
    },
    'help-desc': {
        'en': "Display help message",
        'ru': "Показать справку",
        'be': "Паказаць даведку",
        'uk': "Показати довідку"
    },
    'build-desc': {
        'en': "Create an order",
        'ru': "Cоздать заказ",
        'be': "Стварыць замову",
        'uk': "Створити замовлення"
    },
    'cancel-desc': {
        'en': "Cancel order",
        'ru': "Отменить заказ",
        'be': "Скасаваць замову",
        'uk': "Скасувати замовлення",
    },
    'suggest-cancel': {
        'en': "If you wish to change your order, please send /cancel then /build.",
        'ru': "Если вы желаете изменить заказ, пожалуйста, отправьте /cancel затем /build.",
        'be': "Калі вы жадаеце змяніць замову, калі ласка, дашліце /cancel затым /build.",
        'uk': "Якщо ви бажаєте змінити замовлення, будь ласка, відправте /cancel потім /build.",
    },
    'cannot-cancel': {
        'en': "Sorry, cannot cancel the build in progress. Please wait until the build completes",
        'ru': "Извините, не могу отменить заказ во время сборки. Пожалуйста, дождитесь завершения сборки.",
        'be': "Выбачайце, не магу скасаваць замову падчас зборкі. Калі ласка, дачакайцеся заканчэння зборкі.",
        'uk': "Вибачте, не можу скасувати замовлення підчас збірки. Будь ласка, дочекайтеся закінчення збірки."
    },
    'cannot-create': {
        'en': "Sorry, cannot accept a new order during the build of the current order. Please wait until the build completes.",
        'ru': "Извините, не могу принять новый заказ во время сборки текущего заказа. Пожалуйста, дождитесь завершения сборки.",
        'be': "Выбачайце, не магу прыняць новую замову падчас зборкі бягучай замовы. Калі ласка, дачакайцеся заканчэння зборкі.",
        'uk': "Вибачте, не можу прийняти нове замовлення під час збірки поточного замовлення. Будь ласка, дочекайтеся закінчення збірки."
    },
    'media-files-are-not-allowed': {
        'en': "At this stage media files are not allowed.",
        'ru': "На этом этапе медиа-файлы не разрешены.",
        'be': "На гэтым этапе медыя-файлы не дазволены.",
        'uk': "На цьому етапі медіа-файли не дозволені."
    },
    'unknown-text-response': {
        'en': "Please send /build to start setting up your version of Partisan Telegram.",
        'ru': "Пожалуйста, отправьте /build для начала настройки Вашей версии Партизанского Телеграма.",
        'be': "Калі ласка, дашліце /build для пачатку наладкі Вашай версіі Партызанскага Тэлеграма.",
        'uk': "Будь ласка, надішліть /build для початку налаштування Вашої версії Партизанського Телеграма.",
    },
    'build-ended': {
        'en': "Your partisan telegram has been collected. Install the apk from the post above. Correspondence with the bot will be deleted automatically after {0:.0f} minutes."
              " If you want to delete the conversation right now, click the button below this message.",
        'ru': "Ваш партизанский телеграм собран. Установите apk из сообщения выше. Переписка с ботом удалится автоматически через {0:.0f} минут."
              " Если вы хотите удалить переписку прямо сейчас, нажмите кнопку под этим сообщением.",
        'be': "Ваш партызанскі тэлеграм сабраны. Усталюйце apk з паведамлення вышэй. Перапіска з ботам выдаліцца аўтаматычна праз {0:.0f} хвілін."
              " Калі вы жадаеце выдаліць перапіску прама зараз, націсніце кнопку пад гэтым паведамленнем.",
        'uk': "Ваш партизанський телеграм зібрано. Встановіть apk із повідомлення вище. Листування з ботом буде видалено автоматично через {0:.0f} хвилин."
              " Якщо ви бажаєте видалити листування прямо зараз, натисніть кнопку під цим повідомленням.",
    },
    'clear-bot': {
        'en': "Clear messages",
        'ru': "Очистить переписку",
        'be': "Ачысціць перапіску",
        'uk': "Очистити листування",
    },
    'request-confirmation-again': {
        'en': "Please click one of the buttons above to confirm or cancel the application build.",
        'ru': "Пожалуйста, нажмите на одну из кнопок выше для подтверждения или отмены сборки приложения.",
        'be': "Калі ласка, націсніце на адну з кнопак вышэй для пацверджання або адмены зборкі дадатку.",
        'uk': "Будь ласка, натисніть одну з кнопок вище, щоб підтвердити або скасувати складання додатку.",
    },
}

messages = {k: LocalizedMessage(v) for k, v in MESSAGES.items()}

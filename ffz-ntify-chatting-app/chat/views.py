from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http.response import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from chat.models import Message
from chat.forms import SignUpForm
from chat.serializers import MessageSerializer, UserSerializer,UserUpdateSerializer

from rest_framework import mixins
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response


def index(request):
    if request.user.is_authenticated:
        return redirect('chats')
    if request.method == 'GET':
        return render(request, 'chat/index.html', {})
    if request.method == "POST":
        username, password = request.POST['username'], request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
        else:
            return HttpResponse('{"error": "User does not exist"}')
        return redirect('chats')



@csrf_exempt
def message_list(request, sender=None, receiver=None):
    """
    List all required messages, or create a new message.
    """
    if request.method == 'GET':
        messages = Message.objects.filter(sender_id=sender, receiver_id=receiver, is_read=False)
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        for message in messages:
            message.is_read= True
            message.save()
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        #print("inside message post",request)
        data = JSONParser().parse(request)
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)


def register_view(request):
    """
    Render registration template
    """
    if request.method == 'POST':
        #print("working1")
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user.set_password(password)
            user.save()
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('chats')
    else:
        #print("working2")
        form = SignUpForm()
    template = 'chat/register.html'
    context = {'form':form}
    return render(request, template, context)


def chat_view(request):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        # k=Message.objects.filter(receiver__username=request.user.username).select_related("receiver")
        # #print(k.query)
        # for i in k[0]:
        #     #print("ii",i.send)
        # #print("kkkk",k[0].sender)
        # return k
        # people = Message.objects.raw('SELECT id, first_name FROM myapp_person')
        datas=dict()
        from django.db import connection
        cursor = connection.cursor()
        ids=User.objects.get(username=request.user.username).id
        #print("idsss",ids)
        #print("request username",request.user.username)
        query2="SELECT A.username,A.id,COUNT(B.is_read) FROM auth_user A LEFT JOIN ( SELECT * FROM chat_message WHERE receiver_id="+str(ids)+" and is_read=False) B ON A.id = B.sender_id GROUP BY A.username "
        # query2 = "SELECT * from chat_message where receiver_id="+str(ids)+";"
        # query2="PRAGMA table_info(chat_message);"
        cursor.execute(query2)
        datas['results'] = cursor.fetchall()
        res=[]
        #print("datas",datas)
        for i in datas['results']:
            if str(i[0])!=str(request.user.username):
                temp_dict = dict()
                temp_dict["username"] = i[0]
                temp_dict["id"] = i[1]
                temp_dict["unread"] = i[2]
                res.append(temp_dict)
        #print("res",res)
        return render(request, 'chat/chat.html',
                     {"userss":res})


def message_view(request, sender, receiver):
    if not request.user.is_authenticated:
        return redirect('index')
    if request.method == "GET":
        # #print("inside this vieewww")
        messages = Message.objects.filter(sender_id=receiver, receiver_id=sender)
        # #print("messages",messages)
        for message in messages:
            # #print("messages",message)
            # #print("messages.message",message.message)
            # #print("################")
            message.is_read= True
            message.save()
        return render(request, "chat/messages.html",
                      {'users': User.objects.exclude(username=request.user.username),
                       'receiver': User.objects.get(id=receiver),
                       'messages': Message.objects.filter(sender_id=sender, receiver_id=receiver).exclude(is_deleted=True) |
                                   Message.objects.filter(sender_id=receiver, receiver_id=sender).exclude(is_deleted=True)})

class DeleteMessage(APIView):
    def get(self, request, format=None):
        ids=request.query_params.get('ids').strip('/')
        msg=Message.objects.get(id=ids)
        msg.is_deleted=True
        msg.save()
        sender=msg.sender_id
        receiver=msg.receiver_id
        print("sender",sender)
        print("receiver",receiver)
        print("request.user",request.user.username)
        return render(request, "chat/messages.html",
                      {'users': User.objects.exclude(username=request.user.username),
                       'receiver': User.objects.get(id=receiver),
                       'messages': Message.objects.filter(sender_id=sender, receiver_id=receiver).exclude(is_deleted=True) |
                                   Message.objects.filter(sender_id=receiver, receiver_id=sender).exclude(is_deleted=True)})
        # return JsonResponse({"id":ids}, status=201)

class UserDetails(APIView):

    def get(self, request, id):
        ##print("id",id)
        # pk=request.query_params.get('id').strip('/')
        user = User.objects.get(pk=id)
        serializer = UserSerializer(
            user)
        return render(request, 'chat/userdetails.html',
                      {'user':user })

    def post(self, request, id):
        ##print("id",id)
        # pk=request.query_params.get('id').strip('/')
        user = User.objects.get(pk=id)
        serializer = UserUpdateSerializer(
            user,data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        user = User.objects.get(pk=id)
        return render(request, 'chat/userdetails.html',
                      {'user':user })
        # return Response(serializer.data)
    # def get(self, request, format=None):
    #     ids=request.query_params.get('ids').strip('/')
    #     msg=Message.objects.get(id=ids)
    #     msg.is_deleted=True
    #     msg.save()
    #     return JsonResponse({"id":ids}, status=201)

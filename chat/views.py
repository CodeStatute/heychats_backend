from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from chat.serializers import FindConnectionSerializer, CommonUserInfoSerializer, TextMessageSerializer, ImageMessageSerializer
from chat.models import ChatRoom, TextMessage, ImageMessage
from user.models import User
from django.db.models import Q


# ! finds a chat connection
class FindConnectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            connection_id = request.data.get("connection_id")
            user2 = User.objects.get(connection_id=connection_id)
            connection = FindConnectionSerializer(instance=user2).data

            if connection_id == f"{request.user.connection_id}":
                return Response(
                    {
                        "error": {
                            "message": "You are trying to connect with your own account.",
                            "status": "422"
                        }
                    }, status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            res1 = ChatRoom.objects.filter(
                Q(user1=request.user) & Q(user2=user2))

            res2 = ChatRoom.objects.filter(
                Q(user1=user2) & Q(user2=request.user))

            if res1 or res2:
                return Response({
                    "message": "already connected.", "data": {
                        "connection": connection,
                        "connected": True
                    }
                }, status=status.HTTP_200_OK)

            return Response({
                "message": "connection found.", "data": {
                    "connection": connection,
                    "connected": False
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                "error": {
                    "message": "No connection found with this Id",
                    "status": "404"
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except ValueError:
            return Response({
                "error": {
                    "message": "Invalid id type.",
                    "status": "422"
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        except:
            return Response({
                "error": {
                    "message": "Something went wrong!",
                    "status": "500"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ! creates new chat connection
class CreateConnectionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            user2_id = request.data.get("user2_id")
            user2 = User.objects.get(pk=user2_id)

            res1 = ChatRoom.objects.filter(
                Q(user1=request.user) & Q(user2=user2))

            res2 = ChatRoom.objects.filter(
                Q(user1=user2) & Q(user2=request.user))

            if res1 or res2:
                return Response(
                    {"message": "already connected."}, status=status.HTTP_200_OK
                )

            room = ChatRoom.objects.create(user1=request.user, user2=user2)

            return Response(
                {"message": "connected successfully!"}, status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response({
                "error": {
                    "message": "No user found!",
                    "status": "404"
                }
            }, status=status.HTTP_404_NOT_FOUND)

        except:
            return Response({
                "error": {
                    "message": "Something went wrong!",
                    "status": "500"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ! returns all the chats for an authenticated user
class ChatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            rooms = ChatRoom.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            )

            if not rooms:
                return Response({
                    "error": {
                        "message": "no chats found!",
                        "status": "404"
                    }
                }, status=status.HTTP_404_NOT_FOUND)

            chat_connections = []

            for room in rooms:

                lastTMessage = TextMessage.objects.filter(
                    room_id=room.room_id).order_by("created_at").last()

                lastIMessage = ImageMessage.objects.filter(
                    room_id=room.room_id).order_by("created_at").last()

                lastTowMessages = []

                t = TextMessageSerializer(instance=lastTMessage).data

                if t.get("id") is not None:
                    t["type"] = "text"
                    lastTowMessages.append(t)

                i = ImageMessageSerializer(instance=lastIMessage).data

                if i.get("id") is not None:
                    i["type"] = "image"
                    lastTowMessages.append(i)

                lastTowMessages.sort(key=lambda x: x['created_at'])

                lastMessage = {}

                if len(lastTowMessages) > 0:
                    lastMessage = lastTowMessages.pop()
                    lastMessage = {
                        "message": lastMessage.get("message"),
                        "type": lastMessage.get("type"),
                    }

                if room.user1.id != request.user.id:
                    user = CommonUserInfoSerializer(instance=room.user1).data

                    tMessages = TextMessage.objects.filter(
                        room_id=room.room_id).count()

                    iMessages = ImageMessage.objects.filter(
                        room_id=room.room_id).count()

                    chat_connections.append(
                        {
                            "username": user.get("username"),
                            "profile": user.get("profile"),
                            "room_id": room.room_id,
                            "total_messages": tMessages + iMessages,
                            "lastMessage": lastMessage,
                        }
                    )
                    lastMessage = []

                if room.user1.id == request.user.id:
                    user = CommonUserInfoSerializer(instance=room.user2).data

                    tMessages = TextMessage.objects.filter(
                        room_id=room.room_id).count()

                    iMessages = ImageMessage.objects.filter(
                        room_id=room.room_id).count()

                    chat_connections.append(
                        {
                            "username": user.get("username"),
                            "profile": user.get("profile"),
                            "room_id": room.room_id,
                            "total_messages": tMessages + iMessages,
                            "lastMessage": lastMessage,
                        }
                    )
                    lastMessage = []

            chat_connections.sort(
                key=lambda x: x['total_messages'], reverse=True
            )

            return Response(
                {"message": "all the chat connections.",
                    "data": {"chats": chat_connections}},
                status=status.HTTP_200_OK
            )

        except:
            return Response({
                "error": {
                    "message": "Something went wrong!",
                    "status": "500"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ! Chat messages
class ChatMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        try:
            room_id = request.data.get("room_id")

            records = TextMessage.objects.filter(
                room_id=room_id
            ).order_by("-created_at")[:25]

            irecords = ImageMessage.objects.filter(
                room_id=room_id
            ).order_by("-created_at")[:25]

            messages = []

            for item in records:
                data = TextMessageSerializer(instance=item).data
                data["type"] = "text"
                messages.append(data)

            for item in irecords:
                data = ImageMessageSerializer(instance=item).data
                data["type"] = "image"
                messages.append(data)

            messages.sort(key=lambda x: x['created_at'])

            return Response({
                "message": "all the messages",
                "data": {"messages": messages}
            }, status=status.HTTP_200_OK)

        except:
            return Response({
                "error": {
                    "message": "Something went wrong!",
                    "status": "500"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

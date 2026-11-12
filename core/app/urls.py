from django.urls import path,include
from rest_framework import urlpatterns
from rest_framework.routers import DefaultRouter
from app.viewsets import *

# Create a router and register our viewsets with it.
router = DefaultRouter()


router.register(r'',DefaultViewSet)
# router.register(r'user',UserViewSet)
#router.register(r'address',AddressViewSet)
#router.register(r'banner',BannerViewSet)
#router.register(r'bank',BankViewSet)
# router.register(r'state',StateViewSet)
router.register(r'role',RoleViewSet)
#router.register(r'user_evidence',UserEvidenceView)
#router.register(r'user_file',UserFileView)
# router.register(r'faq_category',Faq_CategoryViewSet)
# router.register(r'faq',FaqViewSet)

# router.register(r'category',CategoryViewSet)
# router.register(r'commission',CommissionViewSet)
# router.register(r'company',CompanyViewSet)
# router.register(r'service',ServiceViewSet)
# router.register(r'gallery',ServiceGalleryViewSet)
# router.register(r'group',GroupViewSet)
# router.register(r'support',SupportViewSet)
# router.register(r'status',StatusViewSet)
# router.register(r'evidence',EvidenceViewSet)
# router.register(r'property',PropertyViewSet)
# router.register(r'feature',FeatureViewSet)
# router.register(r'record',RecordViewSet)
# router.register(r'attribute',AttributeViewSet)
# router.register(r'document',DocumentViewSet)
# router.register(r'basket',BasketViewSet)
# router.register(r'porsant',PorsantViewSet)
router.register(r'shop',ShopView)
#router.register(r'wallet',WalletViewSet)

#Blog
# router.register(r'tag',TagViewSet)
# router.register(r'set',SetViewSet)
#router.register(r'blog',BlogViewSet)



urlpatterns = [
    path('',include(router.urls)),

    # path('category/', CategoryViewSet.as_view({'post': 'create','get':'list','delete':'delete'})),
    # path('category/<int:pk>/', CategoryViewSet.as_view({'patch': 'partial_update'})),
    # path('category/<slug:slug>/', CategoryViewSet.as_view({'get': 'category_retrieve'})),

    path('address/', AddressView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('address/some/', AddressView.as_view({'delete':'delete'})),
    path('address/<int:pk>/', AddressView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('address/status/', AddressView.as_view({'patch': 'access',})),
    path('address/recycle/', BannerView.as_view({'patch': 'recycle',})),

    path('bank/', BankView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('bank/some/', BankView.as_view({'delete':'delete'})),
    path('bank/<str:pk>/', BankView.as_view({'get': 'retrieve','patch': 'partial_update'})),
   
   
    path('banner/', BannerView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('banner/some/', BannerView.as_view({'delete':'delete'})),
    path('banner/<int:pk>/', BannerView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('banner/status/', BannerView.as_view({'patch': 'access',})),
    path('banner/recycle/', BannerView.as_view({'patch': 'recycle',})),
   
   
    path('blog/', BlogView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('blog/some/', BlogView.as_view({'delete':'delete'})),
    path('blog/<int:pk>/', BlogView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('blog/status/', BlogView.as_view({'patch': 'access',})),
    path('blog/recycle/', BlogView.as_view({'patch': 'recycle',})),
   
    path('category/', CategoryView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('category/some/', CategoryView.as_view({'delete':'delete'})),
    path('category/<int:pk>/', CategoryView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('category/status/', CategoryView.as_view({'patch': 'access',})),
    path('category/recycle/', CategoryView.as_view({'patch': 'recycle',})),
    path('category/slug/<str:slug>/', CategoryView.as_view({'get': 'category',})),

    path('company/', CompanyView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('company/some/', CompanyView.as_view({'delete':'delete'})),
    path('company/<int:pk>/', CompanyView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('company/status/', CompanyView.as_view({'patch': 'access',})),
    path('company/recycle/', CompanyView.as_view({'patch': 'recycle',})),
    path('company/slug/<str:slug>/', CompanyView.as_view({'get': 'company',})),
   
    path('evidence/', EvidenceView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('evidence/some/', EvidenceView.as_view({'delete':'delete'})),
    path('evidence/<int:pk>/', EvidenceView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('evidence/status/', EvidenceView.as_view({'patch': 'access',})),
    path('evidence/recycle/', EvidenceView.as_view({'patch': 'recycle',})),
   

    path('faq/category/', FaqCategoryView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('faq/category/some/', FaqCategoryView.as_view({'delete':'delete'})),
    path('faq/category/<int:pk>/', FaqCategoryView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('faq/category/status/', FaqCategoryView.as_view({'patch': 'access',})),
    path('faq/category/recycle/', FaqCategoryView.as_view({'patch': 'recycle',})),
    path('faq/category/slug/<str:slug>/', FaqCategoryView.as_view({'get': 'faq_category',})),

    path('faq/', FaqView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('faq/some/', FaqView.as_view({'delete':'delete'})),
    path('faq/<int:pk>/', FaqView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('faq/status/', FaqView.as_view({'patch': 'access',})),
    path('faq/recycle/', FaqView.as_view({'patch': 'recycle',})),

    path('group/', GroupView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('group/some/', GroupView.as_view({'delete':'delete'})),
    path('group/<int:pk>/', GroupView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('group/status/', GroupView.as_view({'patch': 'access'})),
    path('group/category/', GroupView.as_view({'post': 'category_post','delete': 'category_delete'})),
    path('group/recycle/', GroupView.as_view({'patch': 'recycle',})),
  
    path('grade/', GradeView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('grade/some/', GradeView.as_view({'delete':'delete'})),
    path('grade/<int:pk>/', GradeView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('grade/status/', GradeView.as_view({'patch': 'access',})),
    path('grade/recycle/', GradeView.as_view({'patch': 'recycle',})),
  

    path('porsant/', PorsantView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('porsant/some/', PorsantView.as_view({'delete':'delete'})),
    path('porsant/<int:pk>/', PorsantView.as_view({'get': 'retrieve'})),
    


    path('service/', ServiceView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('service/some/', ServiceView.as_view({'delete':'delete'})),
    path('service/<int:pk>/', ServiceView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('service/status/', ServiceView.as_view({'patch': 'access',})),
    path('service/recycle/', ServiceView.as_view({'patch': 'recycle',})),
    path('service/slug/<str:slug>/', ServiceView.as_view({'get': 'service',})),
    path('service/<str:slug>/related/', ServiceView.as_view({'get': 'related',})),
   

    path('service/gallery/', ServiceGalleryView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('service/gallery/some/', ServiceGalleryView.as_view({'delete':'delete'})),
    path('service/gallery/<int:pk>/', ServiceGalleryView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('service/gallery/status/', ServiceGalleryView.as_view({'patch': 'access',})),
 

    path('service/dependent/', ServiceDependentView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('service/dependent/some/', ServiceDependentView.as_view({'delete':'delete'})),
    path('service/dependent/<int:pk>/', ServiceDependentView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('service/dependent/status/', ServiceDependentView.as_view({'patch': 'access',})),
    path('service/dependent/recycle/', ServiceDependentView.as_view({'patch': 'recycle',})),
 
    
    path('set/', SetView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('set/some/', SetView.as_view({'delete':'delete'})),
    path('set/<int:pk>/', SetView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('set/status/', SetView.as_view({'patch': 'access',})),
    path('set/recycle/', SetView.as_view({'patch': 'recycle',})),
  

    path('status/', StatusView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('status/some/', StatusView.as_view({'delete':'delete'})),
    path('status/<str:pk>/', StatusView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('status/status/', StatusView.as_view({'patch': 'access',})),
    path('status/recycle/', StatusView.as_view({'patch': 'recycle',})),
  

    path('support/', SupportView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('support/some/', SupportView.as_view({'delete':'delete'})),
    path('support/<int:pk>/', SupportView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('support/status/', SupportView.as_view({'patch': 'access',})),
    path('support/recycle/', StatusView.as_view({'patch': 'recycle',})),

    path('tag/', TagView.as_view({'post': 'create'})),
   

    path('user/', UserView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('user/some/', UserView.as_view({'delete':'delete'})),
    path('user/<int:pk>/', UserView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('user/status/', UserView.as_view({'patch': 'access',})),
    path('user/recycle/', UserView.as_view({'patch': 'recycle',})),

    path('user/evidence/', UserEvidenceView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('user/evidence/some/', UserEvidenceView.as_view({'delete':'delete'})),
    path('user/evidence/<int:pk>/', UserEvidenceView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('user/evidence/status/', UserEvidenceView.as_view({'patch': 'access',})),
    path('user/evidence/recycle/', UserFileView.as_view({'patch': 'recycle',})),

    path('user/file/', UserFileView.as_view({'post': 'create','get':'list','delete':'delete'})),
    path('user/file/some/', UserFileView.as_view({'delete':'delete'})),
    path('user/file/<int:pk>/', UserFileView.as_view({'get': 'retrieve','patch': 'partial_update'})),
    path('user/file/status/', UserFileView.as_view({'patch': 'access',})),
    path('user/file/recycle/', UserFileView.as_view({'patch': 'recycle',})),
    
    path('wallet/', WalletView.as_view({'get':'list'})),
    path('wallet/charge/', WalletView.as_view({'post': 'create'})),
   

]

view_urls=[
    # path('payment/<str:token>', payment_test, name='payment'),
    path('payment/<str:token>', payment_test, name='payment'),
    path('mellat/callbak/', mellat_callbak, name='mellat_callbak'),
    path('saman/callbak/', saman_callbak, name='saman_callbak'),
    path('zarinpal/callbak/', zarinpal_callbak, name='zarinpal_callbak'),
]
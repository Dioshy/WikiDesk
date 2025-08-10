# 🚨 CONFIGURATION RAILWAY URGENTE

## ⚠️ PROBLÈME IDENTIFIÉ
Railway n'injecte pas automatiquement DATABASE_URL. Il faut le faire manuellement.

## 🔧 SOLUTION IMMÉDIATE (2 minutes)

### Dans Railway Dashboard :

1. **Aller dans votre projet WikiDesk**

2. **Onglet "Variables"** (dans le menu de gauche)

3. **Cliquer "+ Variable"**

4. **Ajouter cette variable** :
   ```
   Name: DATABASE_URL
   Value: postgresql://postgres:********@trolley.proxy.rlwy.net:20169/railway
   ```
   ⚠️ **IMPORTANT** : Remplacez les ******** par le vrai mot de passe PostgreSQL

5. **Pour trouver le vrai mot de passe** :
   - Cliquez sur votre **service PostgreSQL** dans Railway
   - **Onglet "Variables"**
   - **Cherchez PGPASSWORD** ou **cliquez "Show"** sur Connection URL
   - **Copiez le mot de passe**

6. **Sauvegarder** la variable

## 🎯 VARIABLE EXACTE À AJOUTER

Basé sur vos logs précédents :
```
DATABASE_URL=postgresql://postgres:VOTRE_MOT_DE_PASSE@trolley.proxy.rlwy.net:20169/railway
```

## 🚀 APRÈS AJOUT DE LA VARIABLE

1. **Railway redéploie automatiquement** (1-2 minutes)
2. **Nouveaux logs montreront** :
   ```
   DATABASE_URL found: True
   Using PostgreSQL: postgresql://postgres:...
   ✓ Tables created
   ```
3. **Site accessible** à votre URL Railway

## 💡 ALTERNATIVE SI ÇA NE MARCHE PAS

**Option 1** : Supprimer et recréer le service PostgreSQL dans Railway
**Option 2** : Je peux créer une version qui fonctionne avec SQLite temporairement
**Option 3** : Migrer vers Render.com (plus simple pour PostgreSQL)

## 📞 IMMÉDIAT

**Ajoutez la variable DATABASE_URL maintenant et dans 2 minutes votre site sera en ligne !**

L'URL sera : `web-production-07318.up.railway.app`